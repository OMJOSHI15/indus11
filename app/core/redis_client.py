"""Redis async client."""
import json
import time
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

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


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Serialize and cache a value with a TTL (seconds)."""
    await get_redis().setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> Any | None:
    """Return cached value or None if missing/expired."""
    raw = await get_redis().get(key)
    return json.loads(raw) if raw else None


async def cache_delete(key: str) -> None:
    await get_redis().delete(key)


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
