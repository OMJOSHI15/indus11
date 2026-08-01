"""
Tests for the accuracy evaluation harness. Owner: Member A

Covers the pure metric functions only — no API, no databases — so the suite still
runs offline in CI.
"""
from scripts.evaluate import (
    build_eval_set,
    classify,
    confusion,
    metrics_at,
    precision_recall_f1,
    ring_recall,
    sweep_thresholds,
)


def make_row(score, label, pattern="normal", graph_score=0):
    return {
        "tx_id": "EVAL-TEST",
        "label": label,
        "pattern": pattern,
        "composite_score": score,
        "graph_score": graph_score,
    }


# ── classify ──────────────────────────────────────────────────────────────────

def test_classify_maps_each_band():
    assert classify(0, 40, 70) == "APPROVE"
    assert classify(39, 40, 70) == "APPROVE"
    assert classify(40, 40, 70) == "REVIEW"
    assert classify(69, 40, 70) == "REVIEW"
    assert classify(70, 40, 70) == "BLOCK"
    assert classify(100, 40, 70) == "BLOCK"


def test_classify_matches_decision_engine_bands():
    """Guards against the harness drifting from app/services/decision_engine.py."""
    from app.schemas.transaction import LayerScore, TransactionRequest
    from app.services.decision_engine import make_decision

    tx = TransactionRequest(
        tx_id="TX-EVAL-1", sender_account_id="ACC-001",
        receiver_account_id="ACC-002", amount=100.0,
    )
    for rule, graph, rag in [(5, 0, 0), (20, 15, 10), (40, 20, 15)]:
        response = make_decision(
            tx,
            LayerScore(score=rule, max_score=40),
            LayerScore(score=graph, max_score=30),
            LayerScore(score=rag, max_score=30),
            "reason", 1.0,
        )
        assert classify(response.composite_score, 40, 70) == response.decision.value


# ── precision / recall / F1 ───────────────────────────────────────────────────

def test_precision_recall_f1_basic():
    result = precision_recall_f1(tp=8, fp=2, fn=2)
    assert result["precision"] == 0.8
    assert result["recall"] == 0.8
    assert result["f1"] == 0.8


def test_precision_recall_f1_perfect():
    assert precision_recall_f1(tp=5, fp=0, fn=0) == {
        "precision": 1.0, "recall": 1.0, "f1": 1.0,
    }


def test_precision_recall_f1_handles_empty_without_dividing_by_zero():
    assert precision_recall_f1(tp=0, fp=0, fn=0) == {
        "precision": 0.0, "recall": 0.0, "f1": 0.0,
    }


# ── confusion matrix ──────────────────────────────────────────────────────────

def test_confusion_counts_each_cell():
    rows = [
        make_row(10, "legit"), make_row(35, "legit"),
        make_row(50, "fraud"), make_row(45, "legit"),
        make_row(85, "fraud"), make_row(90, "fraud"),
    ]
    matrix = confusion(rows, 40, 70)
    assert matrix["APPROVE"] == {"fraud": 0, "legit": 2}
    assert matrix["REVIEW"] == {"fraud": 1, "legit": 1}
    assert matrix["BLOCK"] == {"fraud": 2, "legit": 0}


# ── metrics_at ────────────────────────────────────────────────────────────────

def test_flagged_view_counts_review_as_caught_but_blocked_view_does_not():
    """A fraud sent to REVIEW is caught by an analyst but is not auto-stopped."""
    rows = [make_row(50, "fraud"), make_row(80, "fraud"), make_row(5, "legit")]
    metrics = metrics_at(rows, 40, 70)
    assert metrics["flagged"]["recall"] == 1.0     # both fraud rows flagged
    assert metrics["blocked"]["recall"] == 0.5     # only the 80 was blocked


def test_missed_fraud_lowers_recall_not_precision():
    rows = [make_row(10, "fraud"), make_row(80, "fraud")]
    metrics = metrics_at(rows, 40, 70)
    assert metrics["flagged"]["precision"] == 1.0
    assert metrics["flagged"]["recall"] == 0.5


# ── threshold sweep ───────────────────────────────────────────────────────────

def test_sweep_finds_bands_that_separate_the_classes():
    # Fraud sits at 45-55, legit at 5-15 — any review threshold in between is perfect.
    rows = [make_row(s, "fraud") for s in (45, 50, 55)]
    rows += [make_row(s, "legit") for s in (5, 10, 15)]
    best = sweep_thresholds(rows)
    assert best["f1"] == 1.0
    assert 20 <= best["review_threshold"] <= 45


# ── graph ring recall ─────────────────────────────────────────────────────────

def test_ring_recall_counts_only_ring_rows_with_a_graph_score():
    rows = [
        make_row(80, "fraud", pattern="mule_ring", graph_score=12),
        make_row(75, "fraud", pattern="mule_ring", graph_score=0),
        make_row(60, "fraud", pattern="shared_device", graph_score=15),  # not a ring
        make_row(5, "legit"),
    ]
    result = ring_recall(rows)
    assert result["ring_transactions"] == 2
    assert result["graph_flagged"] == 1
    assert result["recall"] == 0.5


def test_ring_recall_on_empty_input_is_zero():
    assert ring_recall([make_row(5, "legit")])["recall"] == 0.0


# ── dataset ───────────────────────────────────────────────────────────────────

def test_eval_set_is_labelled_and_deterministic():
    first, second = build_eval_set(), build_eval_set()
    assert [r["tx_id"] for r in first] == [r["tx_id"] for r in second]
    assert [r["amount"] for r in first] == [r["amount"] for r in second]
    assert {r["label"] for r in first} == {"fraud", "legit"}
    assert all(r["amount"] > 0 and r["currency"] == "INR" for r in first)
    # Both classes present in useful quantity, fraud the minority.
    fraud = sum(1 for r in first if r["label"] == "fraud")
    assert 0 < fraud < len(first) / 2


def test_run_id_namespaces_tx_ids_so_reruns_do_not_collide():
    """The analyze endpoint 409s on a duplicate tx_id — each run needs fresh ids."""
    first = {r["tx_id"] for r in build_eval_set("0801120000")}
    second = {r["tx_id"] for r in build_eval_set("0801130000")}
    assert not (first & second)


# ── LLM response parsing ──────────────────────────────────────────────────────

def test_parse_llm_json_takes_first_object_when_model_echoes_an_example():
    """
    llama3 frequently repeats a few-shot example before its own answer. A greedy
    regex spanned both objects and raised "Extra data"; the parser must stop at
    the first complete object.
    """
    from app.services.rag_pipeline import _parse_llm_json

    content = '{"score": 10, "reason": "example"}\n\n{"score": 25, "reason": "actual"}'
    assert _parse_llm_json(content)["score"] == 10


def test_parse_llm_json_tolerates_fences_and_trailing_prose():
    from app.services.rag_pipeline import _parse_llm_json

    content = 'Here is my analysis:\n```json\n{"score": 22, "reason": "mule ring"}\n```\nHope that helps!'
    parsed = _parse_llm_json(content)
    assert parsed == {"score": 22, "reason": "mule ring"}


def test_parse_llm_json_raises_when_there_is_no_object():
    import pytest as _pytest

    from app.services.rag_pipeline import _parse_llm_json

    with _pytest.raises(ValueError):
        _parse_llm_json("I could not determine a score.")
