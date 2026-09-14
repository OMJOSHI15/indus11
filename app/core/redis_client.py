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


async def increment_velocity(account_id: str, window_seconds: int = 600) -> int:
    """
    Record a transaction event and return how many occurred within the rolling
    window. Uses a sorted set scored by timestamp, so old events age out exactly
    (the INCR/EXPIRE approach resets the whole window on every transaction).
    """
    r = get_redis()
    key = f"velocity:{account_id}"
    now = time.time()
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    return results[2]
