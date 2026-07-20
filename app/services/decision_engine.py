"""
Layer 5 — Decision Engine
Owner: Member C

Aggregates scores from Rule Engine, Graph Analyzer, and RAG Pipeline into a
final APPROVE / REVIEW / BLOCK decision.
"""
from app.config import settings
from app.schemas.transaction import AnalysisResponse, Decision, LayerScore, TransactionRequest
from datetime import datetime


def make_decision(
    tx: TransactionRequest,
    rule_score: LayerScore,
    graph_score: LayerScore,
    rag_score: LayerScore,
    rag_explanation: str,
    processing_time_ms: float,
) -> AnalysisResponse:
    """
    Combine all layer scores into a final fraud decision.

    Scoring bands:
      0-39  → APPROVE
      40-69 → REVIEW
      70+   → BLOCK
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
    )
