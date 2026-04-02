from __future__ import annotations

import functools
import hashlib
import json
import os
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Global Redis connection pool
_redis: Optional[aioredis.Redis] = None

# Key prefix to avoid collisions with other projects sharing the same Redis
KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "hss:")


async def init_redis() -> None:
    """Initialize the Redis connection pool. Call once at app startup."""
    global _redis
    url = os.getenv("REDIS_URL", "redis://redis-cache:6379/0")
    try:
        _redis = aioredis.from_url(
            url,
            decode_responses=True,
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        await _redis.ping()
        logger.info("Redis connected: %s", url.split("@")[-1])
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — caching disabled", exc)
        _redis = None


async def close_redis() -> None:
    """Close the Redis connection pool. Call at app shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


def get_redis() -> Optional[aioredis.Redis]:
    """Return the Redis client or None if unavailable."""
    return _redis


def _key(key: str) -> str:
    """Add project prefix to key."""
    return f"{KEY_PREFIX}{key}"


async def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache. Returns None if miss or Redis unavailable."""
    r = get_redis()
    if not r:
        return None
    try:
        val = await r.get(_key(key))
        if val is not None:
            return json.loads(val)
    except Exception:
        pass
    return None


async def cache_get_raw(key: str) -> Optional[str]:
    """Get raw JSON string from cache without deserializing. Returns None if miss."""
    r = get_redis()
    if not r:
        return None
    try:
        return await r.get(_key(key))
    except Exception:
        pass
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Set a value in cache with TTL (seconds). Fails silently."""
    r = get_redis()
    if not r:
        return
    try:
        await r.set(_key(key), json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    """Delete a key from cache. Fails silently."""
    r = get_redis()
    if not r:
        return
    try:
        await r.delete(_key(key))
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern. Fails silently."""
    r = get_redis()
    if not r:
        return
    try:
        full_pattern = _key(pattern)
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=full_pattern, count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass


def cached_response(prefix: str, ttl: int = 86400):
    """Decorator to cache async endpoint responses in Redis.

    Usage:
        @cached_response("lookup:prefixes", ttl=86400)
        async def list_prefixes(keyword=None, limit=50, offset=0, ...):
            ...

    The cache key includes all non-user kwargs (keyword, limit, offset, etc.).
    The 'current_user' kwarg is excluded from the key so all users share the cache.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from non-user arguments
            key_parts = {}
            for k, v in sorted(kwargs.items()):
                if k in ("current_user",):
                    continue
                if v is not None:
                    key_parts[k] = v
            if key_parts:
                params_hash = hashlib.md5(json.dumps(key_parts, default=str).encode()).hexdigest()[:12]
                cache_key = f"{prefix}:{params_hash}"
            else:
                cache_key = prefix

            # Try cache
            cached = await cache_get(cache_key)
            if cached is not None:
                return cached

            # Call original
            result = await func(*args, **kwargs)

            # Cache the result
            await cache_set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
