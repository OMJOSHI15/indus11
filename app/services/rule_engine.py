"""
Layer 2 — Rule Engine
Owner: Member A

Checks transactions against configurable rules and returns a score (0-40) plus flag reasons.

Rules 6-11 are banking anomaly typologies drawn from the red-flag indicators
that FIU-IND and the RBI publish for suspicious-transaction reporting, and the
FATF money-laundering typologies. Each needs only the sender's own payment
history, which Redis keeps (see redis_client.account_history).
"""
import logging
from datetime import timedelta, timezone

from app.core.redis_client import account_history, increment_velocity
from app.schemas.transaction import LayerScore, TransactionRequest
from app.schemas.risk import AccountProfile

logger = logging.getLogger(__name__)

# Merchant categories that always trigger elevated scrutiny
HIGH_RISK_MERCHANTS = {"crypto_exchange", "wire_transfer", "gambling", "money_service"}

# Maximum transactions allowed within the velocity window (10 minutes)
VELOCITY_LIMIT = 5

# Amount multiple above average that triggers a flag
AMOUNT_ANOMALY_MULTIPLIER = 3.0

# ── Banking anomaly thresholds ────────────────────────────────────────────────
# PMLA requires a cash transaction report at ₹10 lakh; amounts kept just under
# it are the classic structuring pattern.
REPORTING_THRESHOLD = 1_000_000
STRUCTURING_BAND = 0.90            # 90-100% of the threshold
DORMANT_DAYS = 180                 # RBI treats accounts idle for long periods as a mule risk
NEW_PAYEE_MIN_AMOUNT = 50_000      # a first payment to a new beneficiary worth scrutinising
PASS_THROUGH_SHARE = 0.80          # money out is at least 80% of money in within 24 h
PASS_THROUGH_MIN_AMOUNT = 10_000   # ignore everyday small in-and-out spending
FAN_OUT_PAYEES = 5                 # more distinct beneficiaries than this in 24 h
ODD_HOURS_IST = range(0, 5)        # 00:00-04:59 India time
IST = timezone(timedelta(hours=5, minutes=30))


async def run_rule_engine(
    tx: TransactionRequest,
    sender: AccountProfile,
    receiver: AccountProfile,
) -> LayerScore:
    """
    Evaluate a transaction against all rules.
    Returns a LayerScore with score (0-40) and list of triggered flag reasons.

    If the rules cannot run — Redis unreachable for the velocity window, in
    practice — the layer is marked failed rather than raising, which would take
    the whole /analyze request down with it through asyncio.gather(). The
    decision engine then sends the transaction to review.
    """
    try:
        return await _run_rules(tx, sender, receiver)
    except Exception as e:
        logger.warning(f"Rule engine error: {e} — layer marked failed")
        return LayerScore.failure(40, "RULE_ENGINE_ERROR", e)


def _epoch(tx: TransactionRequest) -> float:
    """Transaction time as epoch seconds. Timestamps arrive as naive UTC."""
    ts = tx.timestamp
    return (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).timestamp()


async def _run_rules(
    tx: TransactionRequest,
    sender: AccountProfile,
    receiver: AccountProfile,
) -> LayerScore:
    score = 0
    flags: list[str] = []

    # ── Rule 1: Blacklisted account (40 pts — instant max) ────────────────────
    if sender.is_blacklisted or receiver.is_blacklisted:
        return LayerScore(score=40, max_score=40, flags=["BLACKLISTED_ACCOUNT"])

    now = _epoch(tx)

    # ── Rule 2: Velocity limit ─────────────────────────────────────────────────
    tx_count = await increment_velocity(sender.account_id, window_seconds=600, now=now)
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

    # ── Banking anomalies ──────────────────────────────────────────────────────
    history = await account_history(sender.account_id, receiver.account_id, tx.amount, now)

    # Rule 6: Structuring — just under the ₹10 lakh reporting threshold
    if REPORTING_THRESHOLD * STRUCTURING_BAND <= tx.amount < REPORTING_THRESHOLD:
        score += 10
        flags.append(f"STRUCTURING (₹{tx.amount:.0f} just under ₹{REPORTING_THRESHOLD:,} reporting limit)")

    # Rule 7: Dormant account suddenly active
    if history["last_seen"] is not None:
        idle_days = (now - history["last_seen"]) / 86_400
        if idle_days >= DORMANT_DAYS:
            score += 10
            flags.append(f"DORMANT_ACCOUNT_REACTIVATED (idle {idle_days:.0f} days)")

    # Rule 8: Large first payment to a new beneficiary. An account with no
    # history at all is not a "new beneficiary" case — every payee is new.
    if (
        history["last_seen"] is not None
        and not history["known_payee"]
        and tx.amount >= NEW_PAYEE_MIN_AMOUNT
    ):
        score += 8
        flags.append(f"NEW_BENEFICIARY_HIGH_VALUE (first payment ₹{tx.amount:.0f} to {receiver.account_id})")

    # Rule 9: Pass-through — money received and sent straight on (mule behaviour)
    inbound = history["inbound_24h"]
    if inbound >= PASS_THROUGH_MIN_AMOUNT and tx.amount >= inbound * PASS_THROUGH_SHARE:
        score += 12
        flags.append(f"PASS_THROUGH (sent ₹{tx.amount:.0f} of ₹{inbound:.0f} received in 24 h)")

    # Rule 10: Fan-out — paying many different beneficiaries in a day
    if history["payees_24h"] > FAN_OUT_PAYEES:
        score += 8
        flags.append(f"BENEFICIARY_FAN_OUT ({history['payees_24h']} payees in 24 h)")

    # Rule 11: Above-normal amount at an unusual hour
    hour = tx.timestamp.replace(tzinfo=tx.timestamp.tzinfo or timezone.utc).astimezone(IST).hour
    if hour in ODD_HOURS_IST and tx.amount > max(sender.avg_monthly_transaction, NEW_PAYEE_MIN_AMOUNT):
        score += 5
        flags.append(f"ODD_HOUR_HIGH_VALUE ({hour:02d}:00 IST)")

    return LayerScore(score=min(score, 40), max_score=40, flags=flags)
