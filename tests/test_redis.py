"""Tests for Redis client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from app.db.redis import (
    RedisClient,
    init_redis,
    close_redis,
    get_redis,
    get_redis_client,
    _redis_client,
)


class TestRedisClient:
    """Tests for RedisClient class."""

    def test_client_not_initialized_raises_error(self) -> None:
        """Test accessing client before initialization raises error."""
        client = RedisClient()
        with pytest.raises(RuntimeError, match="Redis not initialized"):
            _ = client.client

    @pytest.mark.asyncio
    async def test_connect_initializes_client(self) -> None:
        """Test connect creates Redis client."""
        client = RedisClient()

        with patch("app.db.redis.redis.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis

            await client.connect()

            mock_from_url.assert_called_once()
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_close_cleans_up(self) -> None:
        """Test close properly cleans up client."""
        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        await client.close()

        # After close, client should be None and close should have been called
        mock_redis.close.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_handles_none_client(self) -> None:
        """Test close handles None client gracefully."""
        client = RedisClient()
        client._client = None

        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_ping_returns_true_on_success(self) -> None:
        """Test ping returns True when Redis is available."""
        client = RedisClient()
        client._client = AsyncMock()
        client._client.ping = AsyncMock(return_value=True)

        result = await client.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_ping_returns_false_on_failure(self) -> None:
        """Test ping returns False when Redis fails."""
        client = RedisClient()
        client._client = AsyncMock()
        client._client.ping = AsyncMock(side_effect=Exception("Connection failed"))

        result = await client.ping()

        assert result is False


class TestUsageTracking:
    """Tests for usage tracking methods."""

    @pytest.mark.asyncio
    async def test_increment_usage(self) -> None:
        """Test incrementing usage."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[100, True])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        client._client = mock_redis

        result = await client.increment_usage("user-123", 50)

        assert result == 100
        mock_pipe.incrby.assert_called()
        mock_pipe.expire.assert_called()

    @pytest.mark.asyncio
    async def test_get_usage_returns_value(self) -> None:
        """Test getting usage returns stored value."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="150")
        client._client = mock_redis

        result = await client.get_usage("user-123")

        assert result == 150

    @pytest.mark.asyncio
    async def test_get_usage_returns_zero_when_no_value(self) -> None:
        """Test getting usage returns 0 when no value exists."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        client._client = mock_redis

        result = await client.get_usage("user-123")

        assert result == 0


class TestRateLimiting:
    """Tests for rate limiting methods."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self) -> None:
        """Test first request creates new limit."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        client._client = mock_redis

        allowed, remaining = await client.check_rate_limit(
            "user-123", "endpoint", limit=100, window=60
        )

        assert allowed is True
        assert remaining == 99

    @pytest.mark.asyncio
    async def test_check_rate_limit_under_limit(self) -> None:
        """Test request under limit is allowed."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="50")
        mock_redis.incr = AsyncMock()
        client._client = mock_redis

        allowed, remaining = await client.check_rate_limit(
            "user-123", "endpoint", limit=100, window=60
        )

        assert allowed is True
        assert remaining == 49

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self) -> None:
        """Test request over limit is denied."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="100")
        client._client = mock_redis

        allowed, remaining = await client.check_rate_limit(
            "user-123", "endpoint", limit=100, window=60
        )

        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_rate_limit_ttl(self) -> None:
        """Test getting rate limit TTL."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=45)
        client._client = mock_redis

        result = await client.get_rate_limit_ttl("user-123", "endpoint")

        assert result == 45

    @pytest.mark.asyncio
    async def test_get_rate_limit_ttl_returns_negative_when_no_key(self) -> None:
        """Test getting TTL returns -1 when key doesn't exist."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=-2)
        client._client = mock_redis

        result = await client.get_rate_limit_ttl("user-123", "endpoint")

        assert result == -1


class TestTokenBlacklist:
    """Tests for token blacklist methods."""

    @pytest.mark.asyncio
    async def test_blacklist_token(self) -> None:
        """Test blacklisting a token."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        client._client = mock_redis

        await client.blacklist_token("jti-123", 3600)

        mock_redis.setex.assert_called_once_with("blacklist:jti-123", 3600, "1")

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self) -> None:
        """Test checking blacklisted token returns True."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        client._client = mock_redis

        result = await client.is_token_blacklisted("jti-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self) -> None:
        """Test checking non-blacklisted token returns False."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        client._client = mock_redis

        result = await client.is_token_blacklisted("jti-123")

        assert result is False


class TestSessionCache:
    """Tests for session cache methods."""

    @pytest.mark.asyncio
    async def test_set_session(self) -> None:
        """Test setting session data."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        client._client = mock_redis

        await client.set_session("user-123", {"tier": "pro", "usage": "100"})

        mock_pipe.hset.assert_called()
        mock_pipe.expire.assert_called()

    @pytest.mark.asyncio
    async def test_get_session_returns_data(self) -> None:
        """Test getting session returns data."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"tier": "pro", "usage": "100"})
        client._client = mock_redis

        result = await client.get_session("user-123")

        assert result == {"tier": "pro", "usage": "100"}

    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_empty(self) -> None:
        """Test getting empty session returns None."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        client._client = mock_redis

        result = await client.get_session("user-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self) -> None:
        """Test deleting session."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()
        client._client = mock_redis

        await client.delete_session("user-123")

        mock_redis.delete.assert_called_once_with("session:user-123")

    @pytest.mark.asyncio
    async def test_update_session_field(self) -> None:
        """Test updating single session field."""
        client = RedisClient()
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock()
        client._client = mock_redis

        await client.update_session_field("user-123", "tier", "enterprise")

        mock_redis.hset.assert_called_once_with("session:user-123", "tier", "enterprise")


class TestModuleFunctions:
    """Tests for module-level functions."""

    @pytest.mark.asyncio
    async def test_init_redis(self) -> None:
        """Test init_redis creates global client."""
        import app.db.redis as redis_module

        with patch.object(RedisClient, "connect", new_callable=AsyncMock):
            await init_redis()

            assert redis_module._redis_client is not None

    @pytest.mark.asyncio
    async def test_close_redis(self) -> None:
        """Test close_redis cleans up global client."""
        import app.db.redis as redis_module

        mock_client = AsyncMock()
        redis_module._redis_client = mock_client

        await close_redis()

        mock_client.close.assert_called_once()
        assert redis_module._redis_client is None

    @pytest.mark.asyncio
    async def test_close_redis_handles_none(self) -> None:
        """Test close_redis handles None client."""
        import app.db.redis as redis_module

        redis_module._redis_client = None

        await close_redis()  # Should not raise

    def test_get_redis_raises_when_not_initialized(self) -> None:
        """Test get_redis raises error when not initialized."""
        import app.db.redis as redis_module

        redis_module._redis_client = None

        with pytest.raises(RuntimeError, match="Redis not initialized"):
            get_redis()

    def test_get_redis_returns_client(self) -> None:
        """Test get_redis returns client when initialized."""
        import app.db.redis as redis_module

        mock_client = MagicMock()
        redis_module._redis_client = mock_client

        result = get_redis()

        assert result == mock_client

    @pytest.mark.asyncio
    async def test_get_redis_client_yields_client(self) -> None:
        """Test get_redis_client yields Redis client."""
        import app.db.redis as redis_module

        mock_client = MagicMock()
        redis_module._redis_client = mock_client

        async for client in get_redis_client():
            assert client == mock_client
