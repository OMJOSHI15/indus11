"""Dashboard statistics routes. Owner: Member C"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.models.transaction import Transaction

router = APIRouter(prefix="/stats", tags=["stats"])

# Written by scripts/evaluate.py; absent until an evaluation has been run.
EVAL_RESULTS_PATH = Path(__file__).resolve().parents[3] / "docs" / "eval-results.json"

# (low, high) inclusive score bands for the histogram
SCORE_BUCKETS = [(0, 19), (20, 39), (40, 59), (60, 79), (80, 100)]
# $bucket boundaries are half-open [b_i, b_{i+1}); 101 makes the last bucket 80–100
BUCKET_BOUNDARIES = [0, 20, 40, 60, 80, 101]


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
            "created_at": tx.created_at,
        }
        for tx in flagged
    ]
