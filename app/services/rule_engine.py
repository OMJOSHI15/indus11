"""
Layer 2 — Rule Engine
Owner: Member A

Checks transactions against configurable rules and returns a score (0-40) plus flag reasons.
"""
from datetime import datetime

from app.core.redis_client import increment_velocity
from app.schemas.transaction import LayerScore, TransactionRequest
from app.schemas.risk import AccountProfile

# Merchant categories that always trigger elevated scrutiny
HIGH_RISK_MERCHANTS = {"crypto_exchange", "wire_transfer", "gambling", "money_service"}

# Maximum transactions allowed within the velocity window (10 minutes)
VELOCITY_LIMIT = 5

# Amount multiple above average that triggers a flag
AMOUNT_ANOMALY_MULTIPLIER = 3.0


async def run_rule_engine(
    tx: TransactionRequest,
    sender: AccountProfile,
    receiver: AccountProfile,
) -> LayerScore:
    """
    Evaluate a transaction against all rules.
    Returns a LayerScore with score (0-40) and list of triggered flag reasons.
    """
    score = 0
    flags: list[str] = []

    # ── Rule 1: Blacklisted account (40 pts — instant max) ────────────────────
    if sender.is_blacklisted or receiver.is_blacklisted:
        return LayerScore(score=40, max_score=40, flags=["BLACKLISTED_ACCOUNT"])

    # ── Rule 2: Velocity limit ─────────────────────────────────────────────────
    tx_count = await increment_velocity(sender.account_id, window_seconds=600)
    if tx_count > VELOCITY_LIMIT:
        score += 15
        flags.append(f"VELOCITY_EXCEEDED ({tx_count} tx in 10 min)")

    # ── Rule 3: Amount anomaly ─────────────────────────────────────────────────
    if (
        sender.avg_monthly_transaction > 0
        and tx.amount > sender.avg_monthly_transaction * AMOUNT_ANOMALY_MULTIPLIER
    ):
        score += 12
        flags.append(
            f"AMOUNT_ANOMALY (₹{tx.amount:.0f} vs avg ₹{sender.avg_monthly_transaction:.0f})"
        )

    # ── Rule 4: High-risk merchant category ───────────────────────────────────
    if tx.merchant_category and tx.merchant_category.lower() in HIGH_RISK_MERCHANTS:
        score += 8
        flags.append(f"HIGH_RISK_MERCHANT ({tx.merchant_category})")

    # ── Rule 5: Elevated sender risk tier ─────────────────────────────────────
    if sender.risk_tier == "high":
        score += 5
        flags.append("HIGH_RISK_SENDER_TIER")
    elif sender.risk_tier == "elevated":
        score += 2
        flags.append("ELEVATED_RISK_SENDER_TIER")

    return LayerScore(score=min(score, 40), max_score=40, flags=flags)
