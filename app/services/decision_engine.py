"""
Layer 5 — Decision Engine
Owner: Member C

Aggregates scores from Rule Engine, Graph Analyzer, and RAG Pipeline into a
final APPROVE / REVIEW / BLOCK decision.
"""
import re

from app.config import settings
from app.schemas.transaction import AnalysisResponse, Decision, LayerScore, TransactionRequest
from datetime import datetime


# Words that appear in the flag codes but carry no identifying information —
# ordinary risk prose says "a standard-risk account" or "the sender's average"
# regardless of what actually fired. Matching on these made the guard pass on
# anything: an LLM reply describing a grocery purchase was accepted for a wire
# transfer flagged HIGH_RISK_MERCHANT, purely on the word "risk".
GENERIC_FLAG_WORDS = frozenset({
    "high", "risk", "elevated", "account", "accounts", "pattern", "tier",
    "amount", "money", "fraud", "error", "exceeded", "detected", "sender",
    "receiver", "within", "hops", "cycle", "cycles",
})

# How a failed layer is named to the analyst.
LAYER_LABELS = {
    "rule_engine": "Rule engine",
    "graph_analyzer": "Graph analyzer",
    "rag_pipeline": "Language model",
}


def _explanation_matches_flags(explanation: str, all_flags: list[str]) -> bool:
    """True if the explanation references at least one triggered flag by name.

    Matches a five-character root rather than the whole word, since prose says
    "blacklist" where the code says BLACKLISTED. The flag's parenthetical
    counts too: a good explanation of HIGH_RISK_MERCHANT (wire_transfer) says
    "wire transfer" and never the word "merchant".
    """
    text = explanation.lower()
    return any(
        word[:5] in text
        for flag in all_flags
        for word in re.split(r"[^A-Za-z]+", flag.lower())
        if len(word) >= 4 and word not in GENERIC_FLAG_WORDS
    )


def make_decision(
    tx: TransactionRequest,
    rule_score: LayerScore,
    graph_score: LayerScore,
    rag_score: LayerScore,
    rag_explanation: str,
    processing_time_ms: float,
    rag_pending: bool = False,
) -> AnalysisResponse:
    """
    Combine all layer scores into a final fraud decision.

    Scoring bands:
      0-39  → APPROVE
      40-69 → REVIEW
      70+   → BLOCK

    `rag_pending=True` marks a provisional call made before the RAG/LLM layer
    has run (see app/api/routes/transactions.py) — the explanation is a
    placeholder, not LLM output, so the flag-matching guard below is skipped.

    A layer whose score has `failed=True` is named in the explanation and
    listed in `layer_failures`, and a transaction that would otherwise be
    approved is sent to review instead.
    """
    composite = rule_score.score + graph_score.score + rag_score.score
    composite = min(composite, 100)

    if composite >= settings.block_threshold:
        decision = Decision.BLOCK
    elif composite >= settings.review_threshold:
        decision = Decision.REVIEW
    else:
        decision = Decision.APPROVE

    layers = {"rule_engine": rule_score, "graph_analyzer": graph_score, "rag_pipeline": rag_score}
    failures = {name: layer.error or "failed" for name, layer in layers.items() if layer.failed}

    # A layer that could not run contributes no evidence, which is not the same
    # as evidence that the transaction is safe: its zero must never approve.
    # A block already earned by the layers that did run is kept.
    if failures and decision == Decision.APPROVE:
        decision = Decision.REVIEW

    # Build explanation from layers + RAG
    all_flags = rule_score.flags + graph_score.flags + rag_score.flags
    if all_flags:
        flag_summary = "Triggered signals: " + "; ".join(all_flags) + ". "
    else:
        flag_summary = "No fraud signals triggered. "

    failure_note = ""
    if failures:
        labels = [LAYER_LABELS[name] for name in failures]
        names = labels[0] if len(labels) == 1 else (
            ", ".join(labels[:-1]) + " and " + labels[-1].lower())
        failure_note = (
            f"{names} failed; the block stands on the layers that ran. "
            if decision == Decision.BLOCK
            else f"{names} failed, so this transaction was sent for review. "
        )

    # ── Guard: the written explanation comes straight from the LLM, which can
    # drift from what the deterministic layers actually flagged. If real
    # signals fired but the explanation doesn't reference any of them by
    # name, don't hand the analyst a confident paragraph that contradicts the
    # evidence — fall back to the flag summary alone. Only flags from layers
    # that ran count as evidence; the words in RULE_ENGINE_ERROR are not.
    evidence = [flag for layer in layers.values() if not layer.failed for flag in layer.flags]
    if rag_score.failed:
        explanation = flag_summary + failure_note       # there is no model text to show
    elif not rag_pending and evidence and not _explanation_matches_flags(rag_explanation, evidence):
        explanation = flag_summary + failure_note + (
            "The generated explanation did not reference the triggered signals, "
            "so only the flags are shown here."
        )
    else:
        explanation = flag_summary + failure_note + rag_explanation

    return AnalysisResponse(
        tx_id=tx.tx_id,
        decision=decision,
        composite_score=composite,
        rule_engine=rule_score,
        graph_analyzer=graph_score,
        rag_pipeline=rag_score,
        explanation=explanation,
        processing_time_ms=processing_time_ms,
        timestamp=datetime.utcnow(),
        rag_pending=rag_pending,
        layer_failures=failures,
    )
