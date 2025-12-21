"""Redis client management.

Redis Key Schema Documentation
==============================

Usage Tracking:
  usage:{user_id}:{week_key}     # Weekly token count
                                 # Type: STRING (integer)
                                 # TTL: 8 days
                                 # Example: usage:550e8400-...:2025-W51 = "15000"

Rate Limiting:
  ratelimit:{user_id}:{endpoint} # Request counter
                                 # Type: STRING (integer)
                                 # TTL: 60 seconds
                                 # Example: ratelimit:550e8400-...:translate = "45"

Token Blacklist:
  blacklist:{token_jti}          # Revoked JWT ID
                                 # Type: STRING ("1")
                                 # TTL: Same as token expiry
                                 # Example: blacklist:abc123 = "1"

Session Cache:
  session:{user_id}              # User session data
                                 # Type: HASH
                                 # TTL: 24 hours
                                 # Fields: tier, usage_this_week, last_active

Real-time:
  ws:connections:{user_id}       # WebSocket connection tracking
                                 # Type: SET (connection IDs)
                                 # TTL: None (managed by connection lifecycle)
"""

from datetime import datetime, timedelta
from typing import Any, AsyncGenerator

import redis.asyncio as redis

from app.config import get_settings


class RedisClient:
    """Redis client with domain-specific operations."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        """Get the underlying Redis client."""
        if self._client is None:
            raise RuntimeError("Redis not initialized. Call connect() first.")
        return self._client

    async def connect(self) -> None:
        """Connect to Redis."""
        settings = get_settings()
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            return await self.client.ping()
        except Exception:
            return False

    # ==================== Usage Tracking ====================

    async def increment_usage(self, user_id: str, tokens: int) -> int:
        """Increment usage counter for the current week.

        Args:
            user_id: User UUID string
            tokens: Number of tokens to add

        Returns:
            New total usage for the week
        """
        week_key = datetime.now().strftime("%Y-W%W")
        key = f"usage:{user_id}:{week_key}"

        pipe = self.client.pipeline()
        pipe.incrby(key, tokens)
        pipe.expire(key, timedelta(days=8))
        results = await pipe.execute()

        return int(results[0])

    async def get_usage(self, user_id: str) -> int:
        """Get current week's usage for a user.

        Args:
            user_id: User UUID string

        Returns:
            Current usage count for the week
        """
        week_key = datetime.now().strftime("%Y-W%W")
        key = f"usage:{user_id}:{week_key}"

        value = await self.client.get(key)
        return int(value) if value else 0

    # ==================== Rate Limiting ====================

    async def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        limit: int = 100,
        window: int = 60,
    ) -> tuple[bool, int]:
        """Check if request is within rate limit.

        Args:
            user_id: User UUID string
            endpoint: Endpoint name (e.g., "translate")
            limit: Maximum requests per window
            window: Time window in seconds

        Returns:
            Tuple of (allowed, remaining_requests)
        """
        key = f"ratelimit:{user_id}:{endpoint}"

        current = await self.client.get(key)
        if current is None:
            await self.client.setex(key, window, 1)
            return True, limit - 1

        count = int(current)
        if count >= limit:
            return False, 0

        await self.client.incr(key)
        return True, limit - count - 1

    async def get_rate_limit_ttl(self, user_id: str, endpoint: str) -> int:
        """Get remaining time until rate limit resets.

        Args:
            user_id: User UUID string
            endpoint: Endpoint name

        Returns:
            Seconds until reset, or -1 if no limit exists
        """
        key = f"ratelimit:{user_id}:{endpoint}"
        ttl = await self.client.ttl(key)
        return ttl if ttl > 0 else -1

    # ==================== Token Blacklist ====================

    async def blacklist_token(self, jti: str, expires_in: int) -> None:
        """Add a token to the blacklist.

        Args:
            jti: JWT ID (unique token identifier)
            expires_in: Seconds until token expiry
        """
        key = f"blacklist:{jti}"
        await self.client.setex(key, expires_in, "1")

    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted
        """
        key = f"blacklist:{jti}"
        return await self.client.exists(key) > 0

    # ==================== Session Cache ====================

    async def set_session(
        self,
        user_id: str,
        data: dict[str, Any],
        ttl: int = 86400,
    ) -> None:
        """Cache user session data.

        Args:
            user_id: User UUID string
            data: Session data to cache
            ttl: Time to live in seconds (default: 24 hours)
        """
        key = f"session:{user_id}"
        pipe = self.client.pipeline()
        pipe.hset(key, mapping={k: str(v) for k, v in data.items()})
        pipe.expire(key, ttl)
        await pipe.execute()

    async def get_session(self, user_id: str) -> dict[str, str] | None:
        """Get cached session data.

        Args:
            user_id: User UUID string

        Returns:
            Session data dict or None if not found
        """
        key = f"session:{user_id}"
        data = await self.client.hgetall(key)
        return data if data else None

    async def delete_session(self, user_id: str) -> None:
        """Delete cached session data.

        Args:
            user_id: User UUID string
        """
        key = f"session:{user_id}"
        await self.client.delete(key)

    async def update_session_field(
        self,
        user_id: str,
        field: str,
        value: str,
    ) -> None:
        """Update a single field in the session cache.

        Args:
            user_id: User UUID string
            field: Field name to update
            value: New value
        """
        key = f"session:{user_id}"
        await self.client.hset(key, field, value)


# Global Redis client instance
_redis_client: RedisClient | None = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global _redis_client
    _redis_client = RedisClient()
    await _redis_client.connect()


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def get_redis() -> RedisClient:
    """Get Redis client singleton."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client


async def get_redis_client() -> AsyncGenerator[RedisClient, None]:
    """Get Redis client for dependency injection."""
    yield get_redis()
