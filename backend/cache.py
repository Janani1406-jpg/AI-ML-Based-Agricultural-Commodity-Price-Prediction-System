"""Redis cache initialization and utilities."""
import redis.asyncio as aioredis
import os, json, logging

logger = logging.getLogger(__name__)
_redis = None

async def init_cache():
    global _redis
    try:
        _redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        await _redis.ping()
        logger.info("Redis cache connected.")
    except Exception as e:
        logger.warning(f"Redis unavailable, running without cache: {e}")
        _redis = None

async def cache_get(key: str):
    if not _redis: return None
    try:
        val = await _redis.get(key)
        return json.loads(val) if val else None
    except Exception: return None

async def cache_set(key: str, value, ttl: int = 300):
    if not _redis: return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception: pass

async def cache_delete(key: str):
    if not _redis: return
    try: await _redis.delete(key)
    except Exception: pass
