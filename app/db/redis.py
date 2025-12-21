"""Redis client management."""

from typing import AsyncGenerator

import redis.asyncio as redis

from app.config import get_settings

# Global Redis client
_redis_client: redis.Redis | None = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global _redis_client

    settings = get_settings()
    _redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Get Redis client for dependency injection."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")

    yield _redis_client
