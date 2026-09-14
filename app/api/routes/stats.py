"""Dashboard statistics routes. Owner: Member C"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.transaction import Transaction

router = APIRouter(prefix="/stats", tags=["stats"])

# Written by scripts/evaluate.py; absent until an evaluation has been run.
EVAL_RESULTS_PATH = Path(__file__).resolve().parents[3] / "docs" / "eval-results.json"

# $bucket boundaries are half-open [b_i, b_{i+1}); 101 makes the last bucket 80-100.
# The (low, high) labels are derived rather than written out twice — a second
# hand-maintained table is a table that eventually disagrees with this one.
BUCKET_BOUNDARIES = [0, 20, 40, 60, 80, 101]
SCORE_BUCKETS = [(lo, hi - 1) for lo, hi in zip(BUCKET_BOUNDARIES, BUCKET_BOUNDARIES[1:])]


@router.get("/risk-distribution", summary="Decision counts and composite score histogram")
async def risk_distribution():
    # Decision counts via aggregation
    decision_rows = await Transaction.aggregate(
        [
            {"$match": {"decision": {"$ne": None}}},
            {"$group": {"_id": "$decision", "count": {"$sum": 1}}},
        ]
    ).to_list()
    decisions = {row["_id"]: row["count"] for row in decision_rows}

    # Composite score histogram via $bucket
    bucket_rows = await Transaction.aggregate(
        [
            {"$match": {"composite_score": {"$ne": None}}},
            {
                "$bucket": {
                    "groupBy": "$composite_score",
                    "boundaries": BUCKET_BOUNDARIES,
                    "default": "other",
                    "output": {"count": {"$sum": 1}},
                }
            },
        ]
    ).to_list()
    counts_by_lower = {row["_id"]: row["count"] for row in bucket_rows}

    return {
        "decisions": {
            "APPROVE": decisions.get("APPROVE", 0),
            "REVIEW": decisions.get("REVIEW", 0),
            "BLOCK": decisions.get("BLOCK", 0),
        },
        "score_histogram": [
            {"bucket": f"{low}-{high}", "count": counts_by_lower.get(low, 0)}
            for low, high in SCORE_BUCKETS
        ],
        "total": sum(decisions.values()),
    }


# Upper bound is a sentinel: $bucket needs a finite last boundary.
AMOUNT_BOUNDARIES = [0, 1_000, 10_000, 100_000, 1_000_000, 10**15]
AMOUNT_LABELS = ["< ₹1K", "₹1K–10K", "₹10K–1L", "₹1L–10L", "₹10L+"]
SIGNAL_PREFIX = "Triggered signals: "
FLAGGED = ["REVIEW", "BLOCK"]


def flag_codes(explanation: str | None) -> list[str]:
    """
    Flag codes from a stored explanation, "Triggered signals: A (x); B. <prose>".
    Details can contain full stops (IP addresses), so the list ends at the first
    ". " outside parentheses. Layer-error codes are failures, not signals.
    """
    if not explanation or not explanation.startswith(SIGNAL_PREFIX):
        return []
    body, depth = explanation[len(SIGNAL_PREFIX):], 0
    end = len(body)
    for i, ch in enumerate(body):
        depth += (ch == "(") - (ch == ")")
        if ch == "." and depth == 0 and body[i + 1:i + 2] in ("", " "):
            end = i
            break
    codes = (part.split(" (", 1)[0].strip() for part in body[:end].split("; "))
    return [c for c in codes if c and not c.endswith("_ERROR")]


def by_decision(rows: list[dict], key: str) -> list[dict]:
    """Pivot [{_id: {key, decision}, count}] into [{key, APPROVE, REVIEW, BLOCK, total}]."""
    table: dict = {}
    for row in rows:
        value, decision = row["_id"][key], row["_id"]["decision"]
        entry = table.setdefault(value, {key: value, "APPROVE": 0, "REVIEW": 0, "BLOCK": 0})
        if decision in entry:
            entry[decision] = row["count"]
    for entry in table.values():
        entry["total"] = entry["APPROVE"] + entry["REVIEW"] + entry["BLOCK"]
    return list(table.values())


class _ExplanationOnly(BaseModel):
    explanation: Optional[str] = None


@router.get("/overview", summary="Aggregates for the analytics dashboard")
async def overview():
    decided = {"$match": {"decision": {"$ne": None}}}
    is_flagged = {"$in": ["$decision", FLAGGED]}

    totals = await Transaction.aggregate([
        decided,
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "flagged": {"$sum": {"$cond": [is_flagged, 1, 0]}},
            "flagged_amount": {"$sum": {"$cond": [is_flagged, "$amount", 0]}},
            "avg_score": {"$avg": "$composite_score"},
            "layer_failures": {"$sum": {"$cond": [
                {"$gt": [{"$size": {"$objectToArray": {"$ifNull": ["$layer_failures", {}]}}}, 0]}, 1, 0]}},
            "rag_pending": {"$sum": {"$cond": ["$rag_pending", 1, 0]}},
        }},
    ]).to_list()

    days = await Transaction.aggregate([
        decided,
        {"$group": {"_id": {"day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                            "decision": "$decision"}, "count": {"$sum": 1}}},
    ]).to_list()

    categories = await Transaction.aggregate([
        decided,
        {"$group": {"_id": {"category": {"$ifNull": ["$merchant_category", "unknown"]},
                            "decision": "$decision"}, "count": {"$sum": 1}}},
    ]).to_list()

    amounts = await Transaction.aggregate([
        decided,
        {"$bucket": {
            "groupBy": "$amount",
            "boundaries": AMOUNT_BOUNDARIES,
            "default": "other",
            "output": {"total": {"$sum": 1}, "flagged": {"$sum": {"$cond": [is_flagged, 1, 0]}}},
        }},
    ]).to_list()
    amount_rows = {row["_id"]: row for row in amounts}

    # Flags are only stored inside the explanation text, so they are counted here
    # rather than in the database. ponytail: scans every flagged record per call;
    # store flags as an array field if the flagged set grows past ~100k.
    signal_counts: dict[str, int] = {}
    async for tx in Transaction.find({"decision": {"$in": FLAGGED}}).project(_ExplanationOnly):
        for code in set(flag_codes(tx.explanation)):
            signal_counts[code] = signal_counts.get(code, 0) + 1

    t = totals[0] if totals else {}
    return {
        "totals": {
            "total": t.get("total", 0),
            "flagged": t.get("flagged", 0),
            "flagged_amount": round(t.get("flagged_amount", 0)),
            "avg_score": round(t.get("avg_score") or 0, 1),
            "layer_failures": t.get("layer_failures", 0),
            "rag_pending": t.get("rag_pending", 0),
        },
        "by_day": sorted(by_decision(days, "day"), key=lambda r: r["day"]),
        "by_category": sorted(by_decision(categories, "category"), key=lambda r: -r["total"]),
        "by_amount": [
            {"band": label,
             "total": amount_rows.get(low, {}).get("total", 0),
             "flagged": amount_rows.get(low, {}).get("flagged", 0)}
            for low, label in zip(AMOUNT_BOUNDARIES, AMOUNT_LABELS)
        ],
        "signals": sorted(({"code": c, "count": n} for c, n in signal_counts.items()),
                          key=lambda r: -r["count"])[:10],
    }


@router.get("/accuracy", summary="Latest accuracy evaluation results")
async def accuracy():
    """
    Precision, recall, F1 and the confusion matrix from the most recent run of
    scripts/evaluate.py. 404s until an evaluation has been run, so the dashboard
    can show an explanatory empty state rather than a broken panel.
    """
    if not EVAL_RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="No evaluation results yet — run: python -m scripts.evaluate",
        )
    return json.loads(EVAL_RESULTS_PATH.read_text())


@router.get("/recent-flags", summary="Recent REVIEW and BLOCK transactions")
async def recent_flags(limit: int = Query(default=20, ge=1, le=100)):
    flagged = (
        await Transaction.find({"decision": {"$in": ["REVIEW", "BLOCK"]}})
        .sort(-Transaction.created_at)
        .limit(limit)
        .to_list()
    )
    return [
        {
            "tx_id": tx.tx_id,
            "sender_account_id": tx.sender_account_id,
            "receiver_account_id": tx.receiver_account_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "merchant_category": tx.merchant_category,
            "composite_score": tx.composite_score,
            "decision": tx.decision,
            "explanation": tx.explanation,
            "layer_failures": tx.layer_failures,
            "created_at": tx.created_at,
        }
        for tx in flagged
    ]
