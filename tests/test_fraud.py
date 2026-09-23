"""
Basic tests for the fraud detection pipeline.
Run with: pytest tests/ -v
"""
import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


NEUTRAL_HISTORY = {
    "last_seen": None, "known_payee": False, "payees_24h": 1, "inbound_24h": 0.0,
    "paid_by_receiver": False, "outbound_24h": [], "receiver_senders_24h": 1,
    "known_device": None, "devices_24h": 0, "known_ip": None, "last_location": None,
    "known_category": False, "merchant_senders_10m": 0,
}


@pytest.fixture(autouse=True)
def no_redis_history():
    """Rule tests run without Redis: the banking-anomaly history reads as a fresh
    account unless a test patches it with something else."""
    with patch("app.services.rule_engine.account_history", new_callable=AsyncMock,
               return_value=dict(NEUTRAL_HISTORY)) as mock:
        yield mock


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
    assert result.failed and "connection refused" in result.error


@pytest.mark.asyncio
async def test_rule_engine_marks_itself_failed_instead_of_raising():
    """Redis down used to raise through asyncio.gather and fail the whole request."""
    with patch("app.services.rule_engine.increment_velocity", new_callable=AsyncMock,
               side_effect=ConnectionError("redis down")):
        result = await run_rule_engine(make_tx(), make_profile(), make_profile(account_id="ACC-002"))
    assert result.failed and result.score == 0
    assert result.flags == ["RULE_ENGINE_ERROR"]
    assert "redis down" in result.error


def test_layer_failure_names_an_exception_that_has_no_message():
    """asyncio.TimeoutError has an empty message; the analyst still needs a reason."""
    assert LayerScore.failure(30, "RAG_PIPELINE_ERROR", asyncio.TimeoutError()).error == "TimeoutError"


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
    # The error travels on the score, where the decision engine names the failed
    # layer; there is no model text to show, so the explanation is empty.
    assert score.failed and "chroma down" in score.error
    assert explanation == ""


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


# ── Layer failure handling ────────────────────────────────────────────────────

def failed_layer(max_score, flag):
    return LayerScore.failure(max_score, flag, ConnectionError("down"))


def test_failed_layer_sends_a_would_be_approval_to_review():
    result = make_decision(make_tx(), failed_layer(40, "RULE_ENGINE_ERROR"), make_layer(0, 30),
                           make_layer(0, 30), "Routine purchase.", 50.0)
    assert result.decision.value == "REVIEW"
    assert result.composite_score == 0
    assert result.layer_failures == {"rule_engine": "ConnectionError: down"}
    assert "Rule engine failed, so this transaction was sent for review" in result.explanation


def test_failed_layer_keeps_a_block_the_other_layers_earned():
    result = make_decision(make_tx(), make_layer(40, 40, ["BLACKLISTED_ACCOUNT"]),
                           failed_layer(30, "GRAPH_ANALYZER_ERROR"), make_layer(30, 30),
                           "Blacklisted sender.", 50.0)
    assert result.decision.value == "BLOCK"
    assert "graph_analyzer" in result.layer_failures
    assert "the block stands on the layers that ran" in result.explanation


def test_failed_language_model_shows_no_model_text_and_skips_the_guard():
    result = make_decision(make_tx(), make_layer(40, 40, ["BLACKLISTED_ACCOUNT"]), make_layer(0, 30),
                           failed_layer(30, "RAG_PIPELINE_ERROR"), "", 50.0)
    assert "Language model failed" in result.explanation
    assert "did not reference" not in result.explanation


def test_error_flag_words_do_not_satisfy_the_explanation_guard():
    """RULE_ENGINE_ERROR is not evidence: prose mentioning "rules" must not pass on it."""
    result = make_decision(make_tx(), failed_layer(40, "RULE_ENGINE_ERROR"),
                           make_layer(15, 30, ["SHARED_DEVICE (8 accounts on device DEV-X)"]),
                           make_layer(10, 30), "Our rules engine saw nothing unusual.", 50.0)
    assert "did not reference the triggered signals" in result.explanation


def test_no_failures_reported_when_every_layer_ran():
    result = make_decision(make_tx(), make_layer(5, 40), make_layer(0, 30), make_layer(0, 30),
                           "Low risk.", 50.0)
    assert result.layer_failures == {}


@pytest.mark.asyncio
async def test_background_timeout_records_the_failure_and_replaces_the_placeholder():
    """Clearing only rag_pending left "Pending —" on four stored records for good."""
    from app.api.routes import transactions as route
    record = MagicMock()
    record.update = AsyncMock()
    fake_model = MagicMock()
    fake_model.find_one.return_value = record
    with patch.object(route, "run_rag_pipeline", new_callable=AsyncMock, side_effect=asyncio.TimeoutError()), \
         patch.object(route, "Transaction", fake_model):
        await route._finish_rag_layer(make_tx(), make_profile(), make_layer(0, 40), make_layer(0, 30), 10.0)
    fields = record.update.await_args.args[0]["$set"]
    assert fields["rag_pending"] is False
    assert fields["decision"] == "REVIEW"
    assert fields["layer_failures"] == {"rag_pipeline": "TimeoutError"}
    assert "Pending" not in fields["explanation"]


@pytest.mark.asyncio
async def test_restarting_an_unknown_component_is_404():
    from app.api.routes.components import restart_component
    with pytest.raises(HTTPException) as exc:
        await restart_component("mongodb")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_restart_resets_the_client_then_reports_the_dependency():
    from app.api.routes import components
    reset = AsyncMock()
    check = AsyncMock(side_effect=ConnectionError("Error 61 connecting to localhost:6390"))
    with patch.dict(components.COMPONENTS, {"rule_engine": ("Rule engine", "Redis", reset, check)}):
        status = await components.restart_component("rule_engine")
    reset.assert_awaited_once()
    assert status["ok"] is False
    assert status["detail"].startswith("Redis is not reachable")


def test_two_failed_layers_are_named_in_one_sentence():
    result = make_decision(make_tx(), failed_layer(40, "RULE_ENGINE_ERROR"), make_layer(0, 30),
                           failed_layer(30, "RAG_PIPELINE_ERROR"), "", 50.0)
    assert "Rule engine and language model failed" in result.explanation


def test_multiline_driver_errors_are_flattened():
    error = LayerScore.failure(30, "GRAPH_ANALYZER_ERROR", RuntimeError("Couldn't connect:\nattempt 1\nattempt 2")).error
    assert "\n" not in error and "attempt 1 attempt 2" in error


def test_flag_codes_survive_full_stops_inside_details():
    from app.api.routes.stats import flag_codes
    text = ("Triggered signals: SHARED_IP (12 accounts on IP 203.0.113.66); HIGH_RISK_SENDER_TIER; "
            "RULE_ENGINE_ERROR (x). Rule engine failed. Model text.")
    assert flag_codes(text) == ["SHARED_IP", "HIGH_RISK_SENDER_TIER"]
    assert flag_codes("No fraud signals triggered. ok") == []
    assert flag_codes(None) == []


def test_by_decision_pivots_counts_and_totals():
    from app.api.routes.stats import by_decision
    rows = [{"_id": {"day": "d1", "decision": "APPROVE"}, "count": 3},
            {"_id": {"day": "d1", "decision": "BLOCK"}, "count": 1}]
    assert by_decision(rows, "day") == [{"day": "d1", "APPROVE": 3, "REVIEW": 0, "BLOCK": 1, "total": 4}]


# ── Banking anomaly rules ─────────────────────────────────────────────────────

async def _rules_with(history=None, sender_kw=None, receiver_kw=None, **tx_kwargs):
    from datetime import datetime
    tx_kwargs.setdefault("timestamp", datetime(2026, 9, 17, 6, 0))   # 11:30 IST, not an odd hour
    tx = make_tx(**tx_kwargs)
    sender = make_profile(**{"avg_monthly_transaction": 0.0, **(sender_kw or {})})
    receiver = make_profile(**{"account_id": "ACC-002", **(receiver_kw or {})})
    with patch("app.services.rule_engine.increment_velocity", new_callable=AsyncMock, return_value=1), \
         patch("app.services.rule_engine.account_history", new_callable=AsyncMock,
               return_value={**NEUTRAL_HISTORY, **(history or {})}):
        return await run_rule_engine(tx, sender, receiver)


def _codes(result):
    return [f.split(" (")[0] for f in result.flags]


@pytest.mark.asyncio
async def test_structuring_just_under_reporting_threshold():
    assert "STRUCTURING" in _codes(await _rules_with(amount=950_000))
    assert "STRUCTURING" not in _codes(await _rules_with(amount=1_000_000))   # at the limit it is reported anyway
    assert "STRUCTURING" not in _codes(await _rules_with(amount=850_000))


@pytest.mark.asyncio
async def test_dormant_account_reactivated_after_180_days():
    from datetime import datetime, timezone
    now = datetime(2026, 9, 17, 6, 0).replace(tzinfo=timezone.utc).timestamp()
    assert "DORMANT_ACCOUNT_REACTIVATED" in _codes(await _rules_with({"last_seen": now - 200 * 86400}))
    assert "DORMANT_ACCOUNT_REACTIVATED" not in _codes(await _rules_with({"last_seen": now - 30 * 86400}))


@pytest.mark.asyncio
async def test_new_beneficiary_needs_history_and_a_large_amount():
    seen = {"last_seen": 1.0, "known_payee": False}
    assert "NEW_BENEFICIARY_HIGH_VALUE" in _codes(await _rules_with(seen, amount=75_000))
    assert "NEW_BENEFICIARY_HIGH_VALUE" not in _codes(await _rules_with(seen, amount=5_000))
    assert "NEW_BENEFICIARY_HIGH_VALUE" not in _codes(await _rules_with({**seen, "known_payee": True}, amount=75_000))
    # a brand-new account has no payees yet, so every payee is "new": not a signal
    assert "NEW_BENEFICIARY_HIGH_VALUE" not in _codes(await _rules_with(amount=75_000))


@pytest.mark.asyncio
async def test_pass_through_when_most_of_the_inflow_leaves_within_a_day():
    assert "PASS_THROUGH" in _codes(await _rules_with({"inbound_24h": 200_000}, amount=190_000))
    assert "PASS_THROUGH" not in _codes(await _rules_with({"inbound_24h": 200_000}, amount=40_000))
    assert "PASS_THROUGH" not in _codes(await _rules_with({"inbound_24h": 3_000}, amount=2_900))
    # sending far more than came in is not forwarding the money on
    assert "PASS_THROUGH" not in _codes(await _rules_with({"inbound_24h": 25_000}, amount=600_000))


@pytest.mark.asyncio
async def test_fan_out_to_many_payees_in_a_day():
    assert "BENEFICIARY_FAN_OUT" in _codes(await _rules_with({"payees_24h": 6}))
    assert "BENEFICIARY_FAN_OUT" not in _codes(await _rules_with({"payees_24h": 5}))


@pytest.mark.asyncio
async def test_odd_hour_uses_india_time_and_needs_a_large_amount():
    from datetime import datetime
    late = datetime(2026, 9, 16, 21, 0)          # 02:30 IST
    assert "ODD_HOUR_HIGH_VALUE" in _codes(await _rules_with(amount=80_000, timestamp=late))
    assert "ODD_HOUR_HIGH_VALUE" not in _codes(await _rules_with(amount=500, timestamp=late))
    assert "ODD_HOUR_HIGH_VALUE" not in _codes(await _rules_with(amount=80_000))   # 11:30 IST


@pytest.mark.asyncio
async def test_anomaly_rules_share_the_rule_engine_cap():
    loud = {"last_seen": 1.0, "known_payee": False, "payees_24h": 9, "inbound_24h": 999_000}
    from datetime import datetime
    result = await _rules_with(loud, amount=960_000, merchant_category="wire_transfer",
                               timestamp=datetime(2026, 9, 16, 21, 0))
    assert result.score == 40 and len(result.flags) >= 6


# ── Extended anomaly rules (12-30): each fires, and stays quiet just outside its condition ──

def _at(offset_seconds):
    from datetime import datetime, timezone
    return datetime(2026, 9, 17, 6, 0).replace(tzinfo=timezone.utc).timestamp() + offset_seconds


EXTENDED_CASES = [
    # code, history, tx kwargs, sender kw, receiver kw, fires
    ("SMURFING", {"outbound_24h": [(_at(-3600), 600_000, "X")]}, {"amount": 500_000}, None, None, True),
    ("SMURFING", {"outbound_24h": [(_at(-3600), 100_000, "X")]}, {"amount": 50_000}, None, None, False),
    ("FAN_IN_COLLECTION_ACCOUNT", {"receiver_senders_24h": 11}, {}, None, None, True),
    ("FAN_IN_COLLECTION_ACCOUNT", {"receiver_senders_24h": 10}, {}, None, None, False),
    ("MICRO_TEST_THEN_LARGE", {"outbound_24h": [(_at(-600), 5, "M")]}, {"amount": 20_000}, None, None, True),
    ("MICRO_TEST_THEN_LARGE", {"outbound_24h": [(_at(-7200), 5, "M")]}, {"amount": 20_000}, None, None, False),
    ("IMPOSSIBLE_TRAVEL", {"last_location": (19.07, 72.87, _at(-1800))},
     {"latitude": 28.61, "longitude": 77.21}, None, None, True),               # Mumbai to Delhi in 30 min
    ("IMPOSSIBLE_TRAVEL", {"last_location": (19.07, 72.87, _at(-6 * 3600))},
     {"latitude": 28.61, "longitude": 77.21}, None, None, False),              # 6 h: a flight
    ("NEW_DEVICE_HIGH_VALUE", {"last_seen": 1.0, "known_device": False}, {"device_id": "D9", "amount": 60_000}, None, None, True),
    ("NEW_DEVICE_HIGH_VALUE", {"last_seen": 1.0, "known_device": True}, {"device_id": "D9", "amount": 60_000}, None, None, False),
    ("NEW_IP_HIGH_VALUE", {"last_seen": 1.0, "known_ip": False}, {"ip_address": "9.9.9.9", "amount": 60_000}, None, None, True),
    ("NEW_IP_HIGH_VALUE", {"last_seen": 1.0, "known_ip": False}, {"ip_address": "9.9.9.9", "amount": 1_000}, None, None, False),
    ("DEVICE_HOPPING", {"devices_24h": 4}, {}, None, None, True),
    ("DEVICE_HOPPING", {"devices_24h": 3}, {}, None, None, False),
    ("DAILY_OUTFLOW_SPIKE", {"outbound_24h": [(_at(-3600), 6_000, "X")]}, {"amount": 5_000},
     {"avg_monthly_transaction": 1_000}, None, True),
    ("DAILY_OUTFLOW_SPIKE", {"outbound_24h": [(_at(-3600), 6_000, "X")]}, {"amount": 3_000},
     {"avg_monthly_transaction": 1_000}, None, False),
    ("REPEATED_ROUND_AMOUNTS", {"outbound_24h": [(_at(-100), 20_000, "X"), (_at(-200), 30_000, "Y")]},
     {"amount": 10_000}, None, None, True),
    ("REPEATED_ROUND_AMOUNTS", {"outbound_24h": [(_at(-100), 20_000, "X"), (_at(-200), 30_000, "Y")]},
     {"amount": 10_500}, None, None, False),
    ("SPLIT_PAYMENTS", {"outbound_24h": [(_at(-100), 4_999, "ACC-002"), (_at(-200), 4_999, "ACC-002")]},
     {"amount": 4_999}, None, None, True),
    ("SPLIT_PAYMENTS", {"outbound_24h": [(_at(-100), 4_999, "ACC-003"), (_at(-200), 4_999, "ACC-004")]},
     {"amount": 4_999}, None, None, False),
    ("BACK_AND_FORTH", {"paid_by_receiver": True}, {}, None, None, True),
    ("BACK_AND_FORTH", {"paid_by_receiver": False}, {}, None, None, False),
    ("NEAR_UPI_LIMIT_REPEATED", {"outbound_24h": [(_at(-100), 95_000, "X")]}, {"amount": 92_000}, None, None, True),
    ("NEAR_UPI_LIMIT_REPEATED", {}, {"amount": 92_000}, None, None, False),
    ("LARGE_FIRST_TRANSACTION", {"last_seen": None}, {"amount": 60_000}, None, None, True),
    ("LARGE_FIRST_TRANSACTION", {"last_seen": 1.0}, {"amount": 60_000}, None, None, False),
    ("FIRST_HIGH_RISK_MERCHANT", {"last_seen": 1.0, "known_category": False}, {"merchant_category": "crypto_exchange"}, None, None, True),
    ("FIRST_HIGH_RISK_MERCHANT", {"last_seen": 1.0, "known_category": True}, {"merchant_category": "crypto_exchange"}, None, None, False),
    ("CURRENCY_MISMATCH", {}, {"currency": "USD"}, {"country_code": "IN"}, None, True),
    ("CURRENCY_MISMATCH", {}, {"currency": "INR"}, {"country_code": "IN"}, None, False),
    ("HIGH_RISK_JURISDICTION", {}, {}, None, {"country_code": "KP"}, True),
    ("HIGH_RISK_JURISDICTION", {}, {}, None, {"country_code": "IN"}, False),
    ("SOCIAL_ENGINEERING_NOTE", {}, {"note": "Urgent KYC update needed"}, None, None, True),
    ("SOCIAL_ENGINEERING_NOTE", {}, {"note": "rent for september"}, None, None, False),
    ("MERCHANT_COLLUSION_BURST", {"merchant_senders_10m": 11}, {"merchant_id": "M1"}, None, None, True),
    ("MERCHANT_COLLUSION_BURST", {"merchant_senders_10m": 10}, {"merchant_id": "M1"}, None, None, False),
    ("ACCOUNT_DRAINING", {"outbound_24h": [(_at(-600), 60_000, "X"), (_at(-1200), 70_000, "Y")]},
     {"amount": 55_000}, None, None, True),
    ("ACCOUNT_DRAINING", {"outbound_24h": [(_at(-7200), 60_000, "X"), (_at(-7300), 70_000, "Y")]},
     {"amount": 55_000}, None, None, False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("code,history,tx_kw,sender_kw,receiver_kw,fires", EXTENDED_CASES,
                         ids=[f"{c[0]}-{'fires' if c[5] else 'quiet'}" for c in EXTENDED_CASES])
async def test_extended_anomaly_rule(code, history, tx_kw, sender_kw, receiver_kw, fires):
    result = await _rules_with(history, sender_kw, receiver_kw, **tx_kw)
    assert not result.failed, result.error
    assert (code in _codes(result)) is fires, result.flags


# ── Audit trail and the pending-record drain ─────────────────────────────────

def test_override_records_the_previous_decision():
    """
    The decision field is overwritten in place, so the record it replaced only
    survives in the override log. Without it nobody can say a BLOCK was ever
    released, or by whom.
    """
    from app.models.transaction import DecisionChange, Transaction

    # Beanie documents need an initialised collection, so the document itself is
    # checked through its schema and the log entry through the plain model.
    overrides = Transaction.model_fields["overrides"]
    assert overrides.default_factory is list, "every transaction starts with an empty log"

    entry = DecisionChange(from_decision="BLOCK", to_decision="APPROVE",
                           actor="reviewer-1", reason="customer confirmed by phone")
    assert (entry.from_decision, entry.to_decision) == ("BLOCK", "APPROVE")
    assert entry.actor == "reviewer-1"
    assert entry.at is not None

    # An override with nothing declared is still recorded, and says so.
    bare = DecisionChange(to_decision="APPROVE")
    assert bare.actor == "unknown" and bare.reason is None


def test_transaction_stores_each_layer_score():
    """The response always carried the split; the record has to keep it too."""
    from app.models.transaction import Transaction

    fields = Transaction.model_fields
    for name in ("rule_score", "graph_score", "rag_score"):
        # None, not zero: a layer that has not run must not read as a clean layer.
        assert fields[name].default is None, f"{name} must default to None"
    # Set only when a record was finished late, so its absence means the
    # explanation is contemporaneous with the decision.
    assert fields["rag_drained_at"].default is None


@pytest.mark.parametrize("explanation,expected", [
    ("Triggered signals: VELOCITY_EXCEEDED; SHARED_DEVICE. The sender moved fast.",
     ["VELOCITY_EXCEEDED", "SHARED_DEVICE"]),
    # The detail holds full stops of its own, so a naive split on ". " loses flags.
    ("Triggered signals: NEW_IP_HIGH_VALUE (first use of 203.0.113.66); STRUCTURING. Prose here.",
     ["NEW_IP_HIGH_VALUE (first use of 203.0.113.66)", "STRUCTURING"]),
    ("Triggered signals: AMOUNT_ANOMALY (sent ₹60000 vs ₹2000 average).",
     ["AMOUNT_ANOMALY (sent ₹60000 vs ₹2000 average)"]),
    ("No signals fired.", []),
    (None, []),
])
def test_signal_parts_keep_the_detail_the_model_needs(explanation, expected):
    """
    The drain script feeds these back to the language model, and the detail is
    the evidence — "sent ₹60000 vs ₹2000 average" is the whole finding. Codes
    alone are what the dashboard aggregate wants, and it strips them itself.
    """
    from app.services.explanation import signal_parts

    assert signal_parts(explanation) == expected


# ── Every write route is behind the key ──────────────────────────────────────
#
# These two go through the app itself rather than the guard function, because
# the regression they exist for is a route that forgets to ask for the guard,
# not a guard that stops working. Neither needs a database: the dependency runs
# before the handler, so a rejected request never reaches MongoDB.

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _mutating_routes():
    from fastapi.routing import APIRoute
    from app.main import app

    return [r for r in app.routes if isinstance(r, APIRoute) and r.methods & MUTATING_METHODS]


def test_every_write_route_requires_the_api_key():
    """
    Catches the case the guard itself cannot: a new write route added without
    asking for it. Every mutating route writes state that later decisions are
    scored against — a transaction, an account profile, a graph label.
    """
    unguarded = [
        f"{sorted(r.methods & MUTATING_METHODS)[0]} {r.path}"
        for r in _mutating_routes()
        if not any(getattr(d, "dependency", None) is require_api_key for d in r.dependencies)
    ]
    assert unguarded == [], f"write routes with no API-key guard: {unguarded}"


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}], ids=["no-key", "wrong-key"])
@pytest.mark.parametrize("method,path,body", [
    ("post", "/api/v1/transactions/analyze",
     {"tx_id": "TX-AUTH", "sender_account_id": "ACC-001", "receiver_account_id": "ACC-002", "amount": 1.0}),
    ("patch", "/api/v1/transactions/TX-AUTH/decision", {"decision": "APPROVE"}),
])
def test_write_routes_reject_a_bad_key(method, path, body, headers):
    from fastapi.testclient import TestClient
    from app.main import app

    # Not entered as a context manager, so the startup hooks never run and the
    # test needs no MongoDB, Neo4j, Redis or language model.
    response = getattr(TestClient(app), method)(path, json=body, headers=headers)
    assert response.status_code == 401, response.text
