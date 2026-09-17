"""Redis async client."""
import json
import logging
import time
import uuid
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
    return _redis


async def reset_redis() -> None:
    """Drop the client and its connection pool so the next call reconnects.
    Used by the component restart route."""
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as e:       # a broken pool may fail to close; the new client is what matters
            logger.warning(f"Closing the Redis client failed: {e}")
    _redis = None


# The cache is best effort: MongoDB is the source of truth, so a Redis outage
# costs a database read, not the request. The velocity window below is not a
# cache — it raises, and the rule engine marks itself failed.
async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Serialize and cache a value with a TTL (seconds)."""
    try:
        await get_redis().setex(key, ttl, json.dumps(value))
    except (RedisError, OSError) as e:
        logger.warning(f"Cache write skipped for {key}: {e}")


async def cache_get(key: str) -> Any | None:
    """Return cached value or None if missing, expired or unreachable."""
    try:
        raw = await get_redis().get(key)
    except (RedisError, OSError) as e:
        logger.warning(f"Cache read skipped for {key}: {e}")
        return None
    return json.loads(raw) if raw else None


async def cache_delete(key: str) -> None:
    try:
        await get_redis().delete(key)
    except (RedisError, OSError) as e:
        logger.warning(f"Cache delete skipped for {key}: {e}")


async def increment_velocity(account_id: str, window_seconds: int = 600, now: float | None = None) -> int:
    """
    Record a transaction event and return how many occurred within the rolling
    window. Uses a sorted set scored by timestamp, so old events age out exactly
    (the INCR/EXPIRE approach resets the whole window on every transaction).
    `now` defaults to the wall clock; a dataset replay passes each transaction's
    own time so the window follows the data rather than the replay speed.
    """
    r = get_redis()
    key = f"velocity:{account_id}"
    now = time.time() if now is None else now
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    return results[2]


DAY = 86_400
HOUR = 3_600
HISTORY_TTL = 400 * DAY  # dormancy is judged over months, so history outlives the velocity window


async def account_history(tx, now: float) -> dict:
    """
    Read what the bank-anomaly rules need about the sender's past, then record
    this transaction, in one round trip. Reads are queued before the writes, so
    they describe the accounts as they were before this payment.

    `tx` is a TransactionRequest. Returns:
      last_seen            epoch seconds of the sender's previous payment, or None
      known_payee          sender has paid this receiver before
      payees_24h           distinct receivers the sender paid in 24 h, this one included
      inbound_24h          total the sender received in 24 h
      paid_by_receiver     the receiver sent the sender money in the last 24 h
      outbound_24h         [(epoch, amount, receiver)] the sender paid in 24 h, before this one
      receiver_senders_24h distinct senders who paid the receiver in 24 h, this one included
      known_device         this device has been used by the sender before (None: no device given)
      devices_24h          distinct devices the sender used in 24 h, this one included
      known_ip             this IP has been used by the sender before (None: no IP given)
      last_location        (lat, lon, epoch) of the sender's previous located payment, or None
      known_category       the sender has paid in this merchant category before
      merchant_senders_10m distinct senders who paid this merchant ID in 10 min (0: no merchant ID)
    """
    s, rcv, amount = tx.sender_account_id, tx.receiver_account_id, tx.amount
    member = f"{now}:{uuid.uuid4().hex[:8]}"
    pipe = get_redis().pipeline()
    idx = {}

    def read(name, _queued):
        # the command is queued when its argument is evaluated, so it is the last one
        idx[name] = len(pipe.command_stack) - 1

    # ── reads (state before this payment) ──
    read("last_seen", pipe.get(f"lastseen:{s}"))
    read("known_payee", pipe.zscore(f"payees:{s}", rcv))
    pipe.zremrangebyscore(f"inbound:{s}", 0, now - DAY)
    read("inbound", pipe.zrangebyscore(f"inbound:{s}", now - DAY, now))
    pipe.zremrangebyscore(f"outbound:{s}", 0, now - DAY)
    read("outbound", pipe.zrangebyscore(f"outbound:{s}", now - DAY, now))
    read("last_location", pipe.get(f"lastloc:{s}"))
    if tx.device_id:
        read("known_device", pipe.zscore(f"devices:{s}", tx.device_id))
    if tx.ip_address:
        read("known_ip", pipe.zscore(f"ips:{s}", tx.ip_address))
    if tx.merchant_category:
        read("known_category", pipe.sismember(f"categories:{s}", tx.merchant_category))

    # ── writes, and counts that include this payment ──
    pipe.set(f"lastseen:{s}", now, ex=HISTORY_TTL)
    pipe.zadd(f"payees:{s}", {rcv: now})
    pipe.expire(f"payees:{s}", HISTORY_TTL)
    read("payees_24h", pipe.zcount(f"payees:{s}", now - DAY, now))
    pipe.zadd(f"outbound:{s}", {f"{member}:{amount}:{rcv}": now})
    pipe.expire(f"outbound:{s}", 2 * DAY)
    pipe.zadd(f"inbound:{rcv}", {f"{member}:{amount}:{s}": now})
    pipe.expire(f"inbound:{rcv}", 2 * DAY)
    pipe.zadd(f"senders:{rcv}", {s: now})
    pipe.expire(f"senders:{rcv}", 2 * DAY)
    read("receiver_senders_24h", pipe.zcount(f"senders:{rcv}", now - DAY, now))
    if tx.device_id:
        pipe.zadd(f"devices:{s}", {tx.device_id: now})
        pipe.expire(f"devices:{s}", HISTORY_TTL)
        read("devices_24h", pipe.zcount(f"devices:{s}", now - DAY, now))
    if tx.ip_address:
        pipe.zadd(f"ips:{s}", {tx.ip_address: now})
        pipe.expire(f"ips:{s}", HISTORY_TTL)
    if tx.latitude is not None and tx.longitude is not None:
        pipe.set(f"lastloc:{s}", f"{tx.latitude},{tx.longitude},{now}", ex=HISTORY_TTL)
    if tx.merchant_category:
        pipe.sadd(f"categories:{s}", tx.merchant_category)
        pipe.expire(f"categories:{s}", HISTORY_TTL)
    if tx.merchant_id:
        pipe.zadd(f"merchant:{tx.merchant_id}", {s: now})
        pipe.zremrangebyscore(f"merchant:{tx.merchant_id}", 0, now - 600)
        pipe.expire(f"merchant:{tx.merchant_id}", HOUR)
        read("merchant_senders_10m", pipe.zcard(f"merchant:{tx.merchant_id}"))

    res = await pipe.execute()
    get = lambda name, default=None: res[idx[name]] if name in idx else default

    # members are "<epoch>:<rand>:<amount>:<counterparty>"
    def parse(members):
        out = []
        for m in members:
            parts = m.split(":", 3)
            out.append((float(parts[0]), float(parts[2]), parts[3] if len(parts) > 3 else None))
        return out

    inbound = parse(get("inbound", []))
    loc = get("last_location")
    lat, lon, ts = loc.split(",") if loc else (None, None, None)
    return {
        "last_seen": float(get("last_seen")) if get("last_seen") is not None else None,
        "known_payee": get("known_payee") is not None,
        "payees_24h": get("payees_24h"),
        "inbound_24h": sum(a for _, a, _ in inbound),
        "paid_by_receiver": any(who == rcv for _, _, who in inbound),
        "outbound_24h": parse(get("outbound", [])),
        "receiver_senders_24h": get("receiver_senders_24h"),
        "known_device": (get("known_device") is not None) if tx.device_id else None,
        "devices_24h": get("devices_24h", 0),
        "known_ip": (get("known_ip") is not None) if tx.ip_address else None,
        "last_location": (float(lat), float(lon), float(ts)) if loc else None,
        "known_category": bool(get("known_category", 0)),
        "merchant_senders_10m": get("merchant_senders_10m", 0),
    }
