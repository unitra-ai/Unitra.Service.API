"""Tests for middleware."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware


# =============================================================================
# Request Logging Middleware Tests
# =============================================================================


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_correlation_id_header(self, async_client: AsyncClient) -> None:
        """Test that response includes X-Correlation-ID header."""
        response = await async_client.get("/api/health/live")

        assert "X-Correlation-ID" in response.headers
        # UUID format check
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) == 36  # UUID length with dashes

    @pytest.mark.asyncio
    async def test_uses_provided_correlation_id(self, async_client: AsyncClient) -> None:
        """Test that provided correlation ID is used."""
        custom_id = "custom-correlation-id-123"
        response = await async_client.get(
            "/api/health/live",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.headers["X-Correlation-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_adds_response_time_header(self, async_client: AsyncClient) -> None:
        """Test that response includes X-Response-Time header."""
        response = await async_client.get("/api/health/live")

        assert "X-Response-Time" in response.headers
        response_time = response.headers["X-Response-Time"]
        assert response_time.endswith("ms")

    @pytest.mark.asyncio
    async def test_response_time_is_positive(self, async_client: AsyncClient) -> None:
        """Test that response time is a positive number."""
        response = await async_client.get("/api/health/live")

        response_time = response.headers["X-Response-Time"]
        time_value = float(response_time.replace("ms", ""))
        assert time_value >= 0

    @pytest.mark.asyncio
    async def test_correlation_id_stored_in_request_state(
        self, async_client: AsyncClient
    ) -> None:
        """Test correlation ID is accessible in request state."""
        # This is tested indirectly through the response header
        response = await async_client.get("/api/health/live")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers


# =============================================================================
# Rate Limit Middleware Tests
# =============================================================================


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def mock_app(self) -> MagicMock:
        """Create a mock ASGI app."""
        return MagicMock()

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.check_rate_limit = AsyncMock(return_value=(True, 99))
        redis.get_rate_limit_ttl = AsyncMock(return_value=60)
        return redis

    @pytest.fixture
    def middleware(self, mock_app: MagicMock, mock_redis: AsyncMock) -> RateLimitMiddleware:
        """Create a RateLimitMiddleware instance."""
        return RateLimitMiddleware(
            app=mock_app,
            redis_client=mock_redis,
            default_limit=100,
            window=60,
        )

    def test_skip_paths_configuration(self, middleware: RateLimitMiddleware) -> None:
        """Test that skip paths are configured correctly."""
        assert "/api/health" in middleware.SKIP_PATHS
        assert "/api/health/live" in middleware.SKIP_PATHS
        assert "/api/health/ready" in middleware.SKIP_PATHS
        assert "/api/version" in middleware.SKIP_PATHS
        assert "/api/docs" in middleware.SKIP_PATHS

    def test_middleware_initialization(
        self, mock_app: MagicMock, mock_redis: AsyncMock
    ) -> None:
        """Test middleware initializes with correct parameters."""
        middleware = RateLimitMiddleware(
            app=mock_app,
            redis_client=mock_redis,
            default_limit=50,
            window=30,
        )

        assert middleware.default_limit == 50
        assert middleware.window == 30

    @pytest.mark.asyncio
    async def test_health_endpoints_skip_rate_limiting(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoints are not rate limited."""
        # Make many requests to health endpoint
        for _ in range(10):
            response = await async_client.get("/api/health/live")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_version_endpoint_skips_rate_limiting(
        self, async_client: AsyncClient
    ) -> None:
        """Test that version endpoint is not rate limited."""
        for _ in range(10):
            response = await async_client.get("/api/version")
            assert response.status_code == 200


# =============================================================================
# Middleware Integration Tests
# =============================================================================


class TestMiddlewareIntegration:
    """Integration tests for middleware chain."""

    @pytest.mark.asyncio
    async def test_all_responses_have_timing_headers(
        self, async_client: AsyncClient
    ) -> None:
        """Test all responses include timing headers."""
        endpoints = [
            "/api/health",
            "/api/health/live",
            "/api/health/ready",
            "/api/version",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert "X-Correlation-ID" in response.headers, f"Missing header for {endpoint}"
            assert "X-Response-Time" in response.headers, f"Missing header for {endpoint}"

    @pytest.mark.asyncio
    async def test_error_responses_have_headers(
        self, async_client: AsyncClient
    ) -> None:
        """Test error responses also include middleware headers."""
        response = await async_client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        assert "X-Correlation-ID" in response.headers
        assert "X-Response-Time" in response.headers

    @pytest.mark.asyncio
    async def test_post_requests_have_headers(
        self, async_client: AsyncClient
    ) -> None:
        """Test POST requests include middleware headers."""
        response = await async_client.post(
            "/api/v1/translate",
            json={"text": "hello", "source_lang": "en", "target_lang": "zh"},
        )

        # Regardless of status code, headers should be present
        assert "X-Correlation-ID" in response.headers
        assert "X-Response-Time" in response.headers

    @pytest.mark.asyncio
    async def test_correlation_id_propagates_through_request(
        self, async_client: AsyncClient
    ) -> None:
        """Test correlation ID is consistent across request lifecycle."""
        custom_id = "test-propagation-id"

        response = await async_client.get(
            "/api/health",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.headers["X-Correlation-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_different_requests_get_different_correlation_ids(
        self, async_client: AsyncClient
    ) -> None:
        """Test each request gets a unique correlation ID."""
        response1 = await async_client.get("/api/health/live")
        response2 = await async_client.get("/api/health/live")

        id1 = response1.headers["X-Correlation-ID"]
        id2 = response2.headers["X-Correlation-ID"]

        assert id1 != id2


# =============================================================================
# Logging Tests
# =============================================================================


class TestMiddlewareLogging:
    """Tests for middleware logging functionality."""

    @pytest.mark.asyncio
    async def test_request_logs_are_generated(
        self, async_client: AsyncClient
    ) -> None:
        """Test that requests generate log entries."""
        # This test verifies the middleware runs without errors
        # Actual log verification would require log capture
        response = await async_client.get("/api/health/live")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_slow_request_timing_captured(
        self, async_client: AsyncClient
    ) -> None:
        """Test that slow requests have accurate timing."""
        response = await async_client.get("/api/health")

        response_time = response.headers["X-Response-Time"]
        time_ms = float(response_time.replace("ms", ""))

        # Response time should be reasonable (less than 10 seconds)
        assert time_ms < 10000
