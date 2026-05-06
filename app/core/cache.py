"""
Redis client + caching primitives.

Modules that need caching call get_cache() to get a typed client and
use the get_or_set helper for read-through caching. Connection is
lazy and singleton — no connection until first call.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from threading import Lock
from typing import Any, TypeVar

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_client: aioredis.Redis | None = None
_lock = Lock()

T = TypeVar("T")


def get_cache() -> aioredis.Redis:
    """
    Singleton Redis client. Initialized on first call, reused after.

    Uses async redis-py (redis.asyncio). The connection pool is managed
    internally by the client; no need to wrap in a context manager.
    """
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client
        _client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("redis_client_initialized", url=_redacted_url())
        return _client


def _redacted_url() -> str:
    """Avoid logging passwords if Redis ever has auth configured."""
    url = settings.REDIS_URL
    if "@" in url:
        # redis://user:pass@host:port → redis://***@host:port
        prefix, rest = url.split("://", 1)
        if "@" in rest:
            _, host = rest.split("@", 1)
            return f"{prefix}://***@{host}"
    return url


async def ping() -> bool:
    """Cheap Redis liveness probe. Used by /health/ready."""
    try:
        return bool(await get_cache().ping())
    except Exception as e:
        logger.warning("redis_ping_failed", error=str(e))
        return False


async def get_or_set(
    key: str,
    ttl_seconds: int,
    loader: Callable[[], Awaitable[T]],
) -> T:
    """
    Read-through cache. If key is hot, return cached value (JSON-decoded).
    Otherwise call loader(), JSON-encode the result, store with TTL, return it.

    Cache failures are non-fatal — if Redis is down, we call loader and
    skip caching. The app keeps working, just slower.
    """
    cache = get_cache()

    try:
        cached = await cache.get(key)
        if cached is not None:
            return json.loads(cached)
    except Exception as e:
        logger.warning("cache_read_failed", key=key, error=str(e))
        # Fall through to loader — degraded but functional

    value = await loader()

    try:
        await cache.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception as e:
        logger.warning("cache_write_failed", key=key, error=str(e))

    return value


async def invalidate(key: str) -> None:
    """Drop a key. Safe to call when key doesn't exist."""
    try:
        await get_cache().delete(key)
    except Exception as e:
        logger.warning("cache_invalidate_failed", key=key, error=str(e))


async def close() -> None:
    """Close the Redis connection pool. Called on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None