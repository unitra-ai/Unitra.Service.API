"""Tests for rate limiting middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.core.middleware import RateLimitMiddleware
from app.core.exceptions import RateLimitError
from app.db.redis import RedisClient


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def create_mock_redis(
        self,
        allowed: bool = True,
        remaining: int = 99,
        ttl: int = 60,
    ) -> AsyncMock:
        """Create mock Redis client."""
        mock_redis = AsyncMock(spec=RedisClient)
        mock_redis.check_rate_limit = AsyncMock(return_value=(allowed, remaining))
        mock_redis.get_rate_limit_ttl = AsyncMock(return_value=ttl)
        return mock_redis

    @pytest.mark.asyncio
    async def test_skips_health_endpoints(self) -> None:
        """Test middleware skips health endpoints."""
        app = FastAPI()
        mock_redis = self.create_mock_redis()

        @app.get("/api/health")
        async def health():
            return {"status": "ok"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        mock_redis.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_live_endpoint(self) -> None:
        """Test middleware skips liveness probe."""
        app = FastAPI()
        mock_redis = self.create_mock_redis()

        @app.get("/api/health/live")
        async def live():
            return {"status": "alive"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health/live")

        assert response.status_code == 200
        mock_redis.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_ready_endpoint(self) -> None:
        """Test middleware skips readiness probe."""
        app = FastAPI()
        mock_redis = self.create_mock_redis()

        @app.get("/api/health/ready")
        async def ready():
            return {"status": "ready"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 200
        mock_redis.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_version_endpoint(self) -> None:
        """Test middleware skips version endpoint."""
        app = FastAPI()
        mock_redis = self.create_mock_redis()

        @app.get("/api/version")
        async def version():
            return {"version": "1.0.0"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/version")

        assert response.status_code == 200
        mock_redis.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self) -> None:
        """Test request under rate limit is allowed."""
        app = FastAPI()
        mock_redis = self.create_mock_redis(allowed=True, remaining=50)

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "ok"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/test")

        assert response.status_code == 200
        assert response.headers.get("X-RateLimit-Limit") == "100"
        assert response.headers.get("X-RateLimit-Remaining") == "50"

    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self) -> None:
        """Test request over rate limit raises RateLimitError."""
        app = FastAPI()
        mock_redis = self.create_mock_redis(allowed=False, remaining=0, ttl=30)

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "ok"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        # When rate limit is exceeded, RateLimitError should be raised
        with pytest.raises(RateLimitError):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/api/test")

    @pytest.mark.asyncio
    async def test_uses_user_id_when_authenticated(self) -> None:
        """Test uses user_id for authenticated requests."""
        from starlette.middleware.base import BaseHTTPMiddleware

        app = FastAPI()
        mock_redis = self.create_mock_redis()

        @app.get("/api/test")
        async def test_endpoint(request: Request):
            return {"user_id": getattr(request.state, "user_id", None)}

        # Create a middleware class to set user_id
        class SetUserIdMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.state.user_id = "test-user-123"
                return await call_next(request)

        # Middleware order: RateLimit runs first (added last), then SetUserId
        # We want SetUserId to run before RateLimit checks
        # So add RateLimit first, then SetUserId
        app.add_middleware(SetUserIdMiddleware)
        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/test")

        assert response.status_code == 200
        # Verify check_rate_limit was called
        mock_redis.check_rate_limit.assert_called()

    @pytest.mark.asyncio
    async def test_uses_ip_when_unauthenticated(self) -> None:
        """Test uses IP address for unauthenticated requests."""
        app = FastAPI()
        mock_redis = self.create_mock_redis()

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "ok"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/test")

        assert response.status_code == 200
        mock_redis.check_rate_limit.assert_called()

    @pytest.mark.asyncio
    async def test_handles_redis_failure_gracefully(self) -> None:
        """Test middleware allows request when Redis fails."""
        app = FastAPI()
        mock_redis = AsyncMock(spec=RedisClient)
        mock_redis.check_rate_limit = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "ok"}

        app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/test")

        # Should allow request when Redis fails
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_limit_and_window(self) -> None:
        """Test middleware uses custom limit and window."""
        app = FastAPI()
        mock_redis = self.create_mock_redis(allowed=True, remaining=199)

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "ok"}

        app.add_middleware(
            RateLimitMiddleware,
            redis_client=mock_redis,
            default_limit=200,
            window=120,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/test")

        assert response.status_code == 200
        assert response.headers.get("X-RateLimit-Limit") == "200"
        assert response.headers.get("X-RateLimit-Reset") == "120"

    def test_skip_paths_constant(self) -> None:
        """Test SKIP_PATHS contains expected paths."""
        expected_paths = {
            "/api/health",
            "/api/health/live",
            "/api/health/ready",
            "/api/version",
            "/api/docs",
            "/api/openapi.json",
        }
        assert RateLimitMiddleware.SKIP_PATHS == expected_paths
