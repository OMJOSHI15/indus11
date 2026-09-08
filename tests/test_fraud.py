"""
Basic tests for the fraud detection pipeline.
Run with: pytest tests/ -v
"""
import pytest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.schemas.transaction import TransactionRequest, LayerScore
from app.schemas.risk import AccountProfile
from app.services.rule_engine import run_rule_engine
from app.services.graph_analyzer import run_graph_analyzer
from app.services.decision_engine import make_decision
from app.core.security import require_api_key


def make_tx(**kwargs) -> TransactionRequest:
    defaults = dict(
        tx_id="TX-TEST-001",
        sender_account_id="ACC-001",
        receiver_account_id="ACC-002",
        amount=100.0,
        currency="CAD",
    )
    defaults.update(kwargs)
    return TransactionRequest(**defaults)


def make_profile(**kwargs) -> AccountProfile:
    defaults = dict(account_id="ACC-001", owner_name="Test User", avg_monthly_transaction=500.0)
    defaults.update(kwargs)
    return AccountProfile(**defaults)


# ── Rule Engine Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_blacklisted_account_returns_max_score():
    tx = make_tx()
    sender = make_profile(is_blacklisted=True)
    receiver = make_profile(account_id="ACC-002")
    with patch("app.services.rule_engine.increment_velocity", new_callable=AsyncMock, return_value=1):
        result = await run_rule_engine(tx, sender, receiver)
    assert result.score == 40
    assert "BLACKLISTED_ACCOUNT" in result.flags


@pytest.mark.asyncio
async def test_amount_anomaly_flag():
    tx = make_tx(amount=5000.0)
    sender = make_profile(avg_monthly_transaction=500.0)
    receiver = make_profile(account_id="ACC-002")
    with patch("app.services.rule_engine.increment_velocity", new_callable=AsyncMock, return_value=1):
        result = await run_rule_engine(tx, sender, receiver)
    assert any("AMOUNT_ANOMALY" in f for f in result.flags)
    assert result.score > 0


@pytest.mark.asyncio
async def test_velocity_exceeded_flag():
    tx = make_tx()
    sender = make_profile()
    receiver = make_profile(account_id="ACC-002")
    with patch("app.services.rule_engine.increment_velocity", new_callable=AsyncMock, return_value=10):
        result = await run_rule_engine(tx, sender, receiver)
    assert any("VELOCITY_EXCEEDED" in f for f in result.flags)


@pytest.mark.asyncio
async def test_clean_transaction_scores_zero():
    tx = make_tx(amount=100.0)
    sender = make_profile(avg_monthly_transaction=1000.0, risk_tier="standard")
    receiver = make_profile(account_id="ACC-002")
    with patch("app.services.rule_engine.increment_velocity", new_callable=AsyncMock, return_value=1):
        result = await run_rule_engine(tx, sender, receiver)
    assert result.score == 0
    assert result.flags == []


# ── Graph Analyzer Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_graph_analyzer_degrades_on_neo4j_failure():
    tx = make_tx(device_id="DEV-001")
    with patch("app.services.graph_analyzer.neo4j_session", side_effect=Exception("connection refused")):
        result = await run_graph_analyzer(tx)
    assert result.score == 0
    assert "GRAPH_ANALYZER_ERROR" in result.flags


# ── API-key guard Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_api_key_rejects_wrong_key():
    with pytest.raises(HTTPException) as exc:
        await require_api_key(x_api_key="wrong-key")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_rejects_missing_key():
    with pytest.raises(HTTPException):
        await require_api_key(x_api_key="")


@pytest.mark.asyncio
async def test_require_api_key_accepts_configured_key():
    from app.config import settings
    await require_api_key(x_api_key=settings.app_secret_key)  # no raise = pass


# ── RAG explainability Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rag_prompt_carries_deterministic_flags():
    """The LLM must see what the rule and graph layers actually found.

    Without this it wrote explanations blind: a blacklisted account on a
    device shared by 8 others was described live as "no unusual merchant
    categories or device fingerprints", scoring 0.
    """
    from app.services import rag_pipeline
    captured = {}

    async def fake_invoke(prompt, inputs):
        captured.update(inputs)
        return '{"score": 20, "explanation": "Blacklisted sender.", "matched_patterns": []}'

    tx = make_tx(merchant_category="retail")
    sender = make_profile()
    with patch.object(rag_pipeline, "_invoke_with_fallback", fake_invoke), \
         patch.object(rag_pipeline, "_get_collection") as coll:
        coll.return_value.count.return_value = 1
        coll.return_value.query.return_value = {"documents": [["a pattern"]], "metadatas": [[{}]]}
        await rag_pipeline.run_rag_pipeline(
            tx, sender, ["BLACKLISTED_ACCOUNT", "SHARED_DEVICE (8 accounts)"]
        )

    assert "BLACKLISTED_ACCOUNT" in captured["deterministic_flags"]
    assert "SHARED_DEVICE" in captured["deterministic_flags"]


@pytest.mark.asyncio
async def test_rag_prompt_handles_no_flags():
    """A clean transaction must render as "(none)", not an empty section."""
    from app.services import rag_pipeline
    captured = {}

    async def fake_invoke(prompt, inputs):
        captured.update(inputs)
        return '{"score": 0, "explanation": "Routine.", "matched_patterns": []}'

    with patch.object(rag_pipeline, "_invoke_with_fallback", fake_invoke), \
         patch.object(rag_pipeline, "_get_collection") as coll:
        coll.return_value.count.return_value = 1
        coll.return_value.query.return_value = {"documents": [["a pattern"]], "metadatas": [[{}]]}
        await rag_pipeline.run_rag_pipeline(make_tx(), make_profile(), [])

    assert captured["deterministic_flags"] == "(none)"


@pytest.mark.asyncio
async def test_rag_returns_score_and_explanation_on_both_paths():
    """Success and failure must return the same (LayerScore, str) shape.

    The caller in app/api/routes/transactions.py used to sniff the return with
    isinstance(..., tuple) because the annotation said LayerScore while both
    branches returned a pair. The dead half of that guard would have replaced a
    real explanation with "RAG pipeline unavailable."
    """
    from app.services import rag_pipeline

    async def fake_invoke(prompt, inputs):
        return '{"score": 12, "explanation": "Wire transfer to a new payee.", "matched_patterns": []}'

    with patch.object(rag_pipeline, "_invoke_with_fallback", fake_invoke), \
         patch.object(rag_pipeline, "_get_collection") as coll:
        coll.return_value.count.return_value = 1
        coll.return_value.query.return_value = {"documents": [["a pattern"]], "metadatas": [[{}]]}
        score, explanation = await rag_pipeline.run_rag_pipeline(make_tx(), make_profile(), [])

    assert score.score == 12
    assert explanation == "Wire transfer to a new payee."

    # Error path: ChromaDB unreachable.
    with patch.object(rag_pipeline, "_get_collection", side_effect=RuntimeError("chroma down")):
        score, explanation = await rag_pipeline.run_rag_pipeline(make_tx(), make_profile(), [])

    assert score.score == 0
    assert score.flags == ["RAG_PIPELINE_ERROR"]
    assert "chroma down" in explanation


# ── Decision Engine Tests ─────────────────────────────────────────────────────

def make_layer(score, max_score, flags=None):
    return LayerScore(score=score, max_score=max_score, flags=flags or [])


def test_decision_approve():
    tx = make_tx()
    result = make_decision(tx, make_layer(5, 40), make_layer(0, 30), make_layer(0, 30), "Low risk.", 50.0)
    assert result.decision.value == "APPROVE"
    assert result.composite_score == 5


def test_decision_review():
    tx = make_tx()
    result = make_decision(tx, make_layer(20, 40), make_layer(15, 30), make_layer(10, 30), "Moderate risk.", 60.0)
    assert result.decision.value == "REVIEW"
    assert result.composite_score == 45


def test_decision_block():
    tx = make_tx()
    result = make_decision(tx, make_layer(40, 40), make_layer(20, 30), make_layer(15, 30), "High risk.", 70.0)
    assert result.decision.value == "BLOCK"
    assert result.composite_score == 75


def test_composite_score_capped_at_100():
    tx = make_tx()
    result = make_decision(tx, make_layer(40, 40), make_layer(30, 30), make_layer(30, 30), "Max risk.", 80.0)
    assert result.composite_score == 100


def test_explanation_falls_back_when_it_ignores_triggered_flags():
    tx = make_tx()
    result = make_decision(
        tx, make_layer(40, 40, ["BLACKLISTED_ACCOUNT"]), make_layer(0, 30), make_layer(0, 30),
        "This customer travels frequently for work.", 50.0,
    )
    assert "did not reference the triggered signals" in result.explanation


def test_explanation_kept_when_it_matches_flags():
    tx = make_tx()
    result = make_decision(
        tx, make_layer(40, 40, ["BLACKLISTED_ACCOUNT"]), make_layer(0, 30), make_layer(0, 30),
        "Sender is on the institutional blacklist.", 50.0,
    )
    assert "institutional blacklist" in result.explanation


def test_explanation_guard_ignores_generic_risk_words():
    """Regression: a live wire transfer got an explanation about a grocery
    purchase, and the guard passed it because HIGH_RISK_MERCHANT contains
    the word "risk", which appears in almost any risk prose."""
    tx = make_tx()
    result = make_decision(
        tx, make_layer(8, 40, ["HIGH_RISK_MERCHANT (wire_transfer)"]),
        make_layer(0, 30), make_layer(2, 30),
        "A small grocery purchase well within the sender's normal monthly "
        "spending, from a standard-risk account.", 50.0,
    )
    assert "did not reference the triggered signals" in result.explanation


def test_explanation_guard_matches_on_flag_detail():
    """A good wire-transfer explanation says "wire transfer", never "merchant" —
    the parenthetical detail has to count as a match."""
    tx = make_tx()
    result = make_decision(
        tx, make_layer(8, 40, ["HIGH_RISK_MERCHANT (wire_transfer)"]),
        make_layer(0, 30), make_layer(22, 30),
        "A wire transfer more than 15x the sender's monthly average.", 50.0,
    )
    assert "15x" in result.explanation


def test_pending_rag_explanation_skips_validation():
    tx = make_tx()
    result = make_decision(
        tx, make_layer(40, 40, ["BLACKLISTED_ACCOUNT"]), make_layer(0, 30), make_layer(0, 30),
        "Pending — the written explanation attaches once the language model finishes.",
        50.0, rag_pending=True,
    )
    assert result.rag_pending is True
    assert "Pending" in result.explanation
