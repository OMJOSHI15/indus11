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
    """
    composite = rule_score.score + graph_score.score + rag_score.score
    composite = min(composite, 100)

    if composite >= settings.block_threshold:
        decision = Decision.BLOCK
    elif composite >= settings.review_threshold:
        decision = Decision.REVIEW
    else:
        decision = Decision.APPROVE

    # Build explanation from layers + RAG
    all_flags = rule_score.flags + graph_score.flags + rag_score.flags
    if all_flags:
        flag_summary = "Triggered signals: " + "; ".join(all_flags) + ". "
    else:
        flag_summary = "No fraud signals triggered. "

    # ── Guard: the written explanation comes straight from the LLM, which can
    # drift from what the deterministic layers actually flagged. If real
    # signals fired but the explanation doesn't reference any of them by
    # name, don't hand the analyst a confident paragraph that contradicts the
    # evidence — fall back to the flag summary alone.
    if not rag_pending and all_flags and not _explanation_matches_flags(rag_explanation, all_flags):
        explanation = flag_summary + (
            "The generated explanation did not reference the triggered signals, "
            "so only the flags are shown here."
        )
    else:
        explanation = flag_summary + rag_explanation

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
    )
