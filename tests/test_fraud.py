"""
Basic tests for the fraud detection pipeline.
Run with: pytest tests/ -v
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.transaction import TransactionRequest, LayerScore
from app.schemas.risk import AccountProfile
from app.services.rule_engine import run_rule_engine
from app.services.decision_engine import make_decision


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
