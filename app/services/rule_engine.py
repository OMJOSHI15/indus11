"""
Layer 2 — Rule Engine
Owner: Member A

Checks transactions against configurable rules and returns a score (0-40) plus flag reasons.

Rules 6-30 are banking anomaly typologies drawn from the red-flag indicators
that FIU-IND and the RBI publish for suspicious-transaction reporting, the
FATF money-laundering typologies, and card-network fraud patterns. Each needs
only the transaction and the accounts' recent history, which Redis keeps (see
redis_client.account_history). Anomalies that need data this system does not
collect (KYC, balances, channels, login events) are listed in the report.
"""
import logging
import math
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
PASS_THROUGH_SHARE = 0.80          # money out is 80-110% of money in within 24 h: forwarded,
PASS_THROUGH_CEILING = 1.10        # not a large payment that merely followed a small credit
PASS_THROUGH_MIN_AMOUNT = 10_000   # ignore everyday small in-and-out spending
FAN_OUT_PAYEES = 5                 # more distinct beneficiaries than this in 24 h
ODD_HOURS_IST = range(0, 5)        # 00:00-04:59 India time
IST = timezone(timedelta(hours=5, minutes=30))

LARGE_AMOUNT = 50_000              # "high value" wherever a rule needs one
SMURF_MIN_PAYMENTS = 2             # payments that together cross the reporting threshold
FAN_IN_SENDERS = 10                # more distinct senders into one account than this in 24 h
MICRO_TEST_MAX = 10                # a probe payment of ₹10 or less...
MICRO_TEST_FOLLOW_UP = 10_000      # ...followed within an hour by one at least this large
IMPOSSIBLE_SPEED_KMH = 900         # faster than an airliner
IMPOSSIBLE_MIN_KM = 100            # ignore GPS jitter and neighbouring towns
DEVICE_HOP_LIMIT = 3               # more devices than this on one account in 24 h
DAILY_SPIKE_MULTIPLIER = 10        # 24 h outflow against the account's usual payment
ROUND_UNIT = 10_000
ROUND_REPEAT = 3                   # round-amount payments in 24 h, this one included
SPLIT_REPEAT = 3                   # identical payments to the same payee in 24 h, this one included
UPI_DAILY_LIMIT = 100_000
UPI_NEAR_LIMIT_REPEAT = 2
MERCHANT_BURST_SENDERS = 10        # distinct payers of one merchant ID in 10 minutes
DRAIN_LARGE_PAYMENTS = 3           # large payments within an hour, this one included

# FATF "black" and "grey" lists (call for action / increased monitoring).
# ponytail: a constant, and FATF revises these three times a year — check
# fatf-gafi.org after each plenary and update, or load it from a file if it churns.
HIGH_RISK_JURISDICTIONS = {
    "KP", "IR", "MM",                                                   # call for action
    "DZ", "AO", "BO", "BG", "BF", "CM", "CI", "CD", "HT", "KE", "LA",    # increased monitoring
    "LB", "MC", "MZ", "NA", "NP", "NG", "ZA", "SS", "SY", "VE", "VN",
    "VG", "YE",
}

# Phrases fraudsters use to rush a victim into paying (RBI and CERT-In advisories).
SOCIAL_ENGINEERING_PHRASES = (
    "kyc", "lottery", "prize", "refund", "urgent", "otp", "customs", "parcel",
    "electricity", "disconnection", "job offer", "work from home", "investment return",
    "double your", "cashback", "arrest", "police", "courier",
)


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
    history = await account_history(tx, now)

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
    if inbound >= PASS_THROUGH_MIN_AMOUNT and inbound * PASS_THROUGH_SHARE <= tx.amount <= inbound * PASS_THROUGH_CEILING:
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

    for points, flag in _extended_anomalies(tx, sender, receiver, history, now):
        score += points
        flags.append(flag)

    return LayerScore(score=min(score, 40), max_score=40, flags=flags)


def _km_between(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _extended_anomalies(tx, sender, receiver, h: dict, now: float) -> list[tuple[int, str]]:
    """Rules 12-30. Returns (points, flag) for each rule that fires."""
    out: list[tuple[int, str]] = []
    amount = tx.amount
    has_history = h["last_seen"] is not None
    earlier = h["outbound_24h"]                           # [(epoch, amount, receiver)] before this one
    day = earlier + [(now, amount, tx.receiver_account_id)]
    last_hour = [p for p in day if p[0] >= now - 3_600]

    # 12 Smurfing: several payments under the threshold that together cross it
    under = [a for _, a, _ in day if a < REPORTING_THRESHOLD]
    if len(under) >= SMURF_MIN_PAYMENTS and sum(under) >= REPORTING_THRESHOLD and amount < REPORTING_THRESHOLD:
        out.append((12, f"SMURFING ({len(under)} payments totalling ₹{sum(under):.0f} in 24 h)"))

    # 13 Fan-in: many different senders into one account (collection or mule account)
    if h["receiver_senders_24h"] > FAN_IN_SENDERS:
        out.append((8, f"FAN_IN_COLLECTION_ACCOUNT ({h['receiver_senders_24h']} senders to {tx.receiver_account_id} in 24 h)"))

    # 14 Micro-testing: tiny probe payments followed by a large one
    probes = [p for p in earlier if p[0] >= now - 3_600 and p[1] <= MICRO_TEST_MAX]
    if probes and amount >= MICRO_TEST_FOLLOW_UP:
        out.append((10, f"MICRO_TEST_THEN_LARGE ({len(probes)} probe payment(s) of ≤ ₹{MICRO_TEST_MAX} in the last hour)"))

    # 15 Impossible travel between two located payments
    if tx.latitude is not None and tx.longitude is not None and h["last_location"]:
        lat, lon, then = h["last_location"]
        km = _km_between(lat, lon, tx.latitude, tx.longitude)
        seconds = max(now - then, 1)
        if km >= IMPOSSIBLE_MIN_KM and km / (seconds / 3_600) > IMPOSSIBLE_SPEED_KMH:
            gap = f"{seconds / 60:.0f} min" if seconds >= 60 else f"{seconds:.0f} s"
            out.append((12, f"IMPOSSIBLE_TRAVEL ({km:.0f} km in {gap})"))

    # 16 New device on an established account, for a large payment
    if has_history and h["known_device"] is False and amount >= LARGE_AMOUNT:
        out.append((8, f"NEW_DEVICE_HIGH_VALUE ({tx.device_id})"))

    # 17 New IP on an established account, for a large payment
    if has_history and h["known_ip"] is False and amount >= LARGE_AMOUNT:
        out.append((6, f"NEW_IP_HIGH_VALUE ({tx.ip_address})"))

    # 18 Device hopping
    if h["devices_24h"] > DEVICE_HOP_LIMIT:
        out.append((8, f"DEVICE_HOPPING ({h['devices_24h']} devices in 24 h)"))

    # 19 Daily outflow far above the account's usual payment
    usual = sender.avg_monthly_transaction
    total_day = sum(a for _, a, _ in day)
    if usual > 0 and len(day) >= 2 and total_day > usual * DAILY_SPIKE_MULTIPLIER:
        out.append((8, f"DAILY_OUTFLOW_SPIKE (₹{total_day:.0f} in 24 h vs usual ₹{usual:.0f})"))

    # 20 Repeated round amounts
    round_ones = [a for _, a, _ in day if a >= ROUND_UNIT and a % ROUND_UNIT == 0]
    if amount >= ROUND_UNIT and amount % ROUND_UNIT == 0 and len(round_ones) >= ROUND_REPEAT:
        out.append((5, f"REPEATED_ROUND_AMOUNTS ({len(round_ones)} round-amount payments in 24 h)"))

    # 21 Split payments: the same amount to the same payee again and again
    same = [p for p in day if p[2] == tx.receiver_account_id and abs(p[1] - amount) < 0.01]
    if len(same) >= SPLIT_REPEAT:
        out.append((8, f"SPLIT_PAYMENTS ({len(same)} × ₹{amount:.0f} to {tx.receiver_account_id} in 24 h)"))

    # 22 Back-and-forth: the receiver paid the sender in the last day
    if h["paid_by_receiver"]:
        out.append((8, f"BACK_AND_FORTH ({tx.receiver_account_id} paid {tx.sender_account_id} in the last 24 h)"))

    # 23 Repeatedly just under the UPI daily limit
    near_upi = [a for _, a, _ in day if 0.9 * UPI_DAILY_LIMIT <= a < UPI_DAILY_LIMIT]
    if 0.9 * UPI_DAILY_LIMIT <= amount < UPI_DAILY_LIMIT and len(near_upi) >= UPI_NEAR_LIMIT_REPEAT:
        out.append((6, f"NEAR_UPI_LIMIT_REPEATED ({len(near_upi)} payments just under ₹{UPI_DAILY_LIMIT:,} in 24 h)"))

    # 24 A brand-new account whose first payment is large
    if not has_history and amount >= LARGE_AMOUNT:
        out.append((6, f"LARGE_FIRST_TRANSACTION (₹{amount:.0f})"))

    # 25 First-ever payment to a high-risk merchant category, from an established account
    if (has_history and tx.merchant_category in HIGH_RISK_MERCHANTS
            and not h["known_category"]):
        out.append((6, f"FIRST_HIGH_RISK_MERCHANT ({tx.merchant_category})"))

    # 26 Foreign currency on an Indian account
    if sender.country_code == "IN" and (tx.currency or "INR").upper() != "INR":
        out.append((4, f"CURRENCY_MISMATCH ({tx.currency} on an Indian account)"))

    # 27 Receiver in a FATF high-risk jurisdiction
    if receiver.country_code.upper() in HIGH_RISK_JURISDICTIONS:
        out.append((10, f"HIGH_RISK_JURISDICTION (receiver in {receiver.country_code.upper()})"))

    # 28 Payment note reads like a scam script
    note = (tx.note or "").lower()
    hits = [p for p in SOCIAL_ENGINEERING_PHRASES if p in note]
    if hits:
        out.append((8, f"SOCIAL_ENGINEERING_NOTE (mentions {', '.join(hits[:3])})"))

    # 29 Many different payers to one merchant ID in a burst
    if h["merchant_senders_10m"] > MERCHANT_BURST_SENDERS:
        out.append((10, f"MERCHANT_COLLUSION_BURST ({h['merchant_senders_10m']} payers to {tx.merchant_id} in 10 min)"))

    # 30 Account draining: several large payments within an hour
    large_hour = [p for p in last_hour if p[1] >= LARGE_AMOUNT]
    if amount >= LARGE_AMOUNT and len(large_hour) >= DRAIN_LARGE_PAYMENTS:
        out.append((10, f"ACCOUNT_DRAINING ({len(large_hour)} payments ≥ ₹{LARGE_AMOUNT:,} in 1 h)"))

    return out
