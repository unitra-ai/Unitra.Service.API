"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient

# =============================================================================
# Health Endpoint Integration Tests
# =============================================================================


class TestHealthEndpoints:
    """Integration tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_200(self, async_client: AsyncClient) -> None:
        """Test /api/health returns 200."""
        response = await async_client.get("/api/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, async_client: AsyncClient) -> None:
        """Test /api/health response has correct structure."""
        response = await async_client.get("/api/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_health_components_structure(self, async_client: AsyncClient) -> None:
        """Test health components have correct structure."""
        response = await async_client.get("/api/health")
        data = response.json()

        components = data["components"]
        assert "database" in components
        assert "redis" in components

        for component in components.values():
            assert "status" in component
            assert component["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_live_returns_alive(self, async_client: AsyncClient) -> None:
        """Test /api/health/live returns alive status."""
        response = await async_client.get("/api/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_health_live_is_fast(self, async_client: AsyncClient) -> None:
        """Test /api/health/live responds quickly."""
        response = await async_client.get("/api/health/live")

        # Parse response time from header
        response_time = response.headers.get("X-Response-Time", "999ms")
        time_ms = float(response_time.replace("ms", ""))

        # Should be very fast (under 100ms)
        assert time_ms < 100

    @pytest.mark.asyncio
    async def test_health_ready_returns_503_without_deps(self, async_client: AsyncClient) -> None:
        """Test /api/health/ready returns 503 when dependencies unavailable."""
        response = await async_client.get("/api/health/ready")

        # Without actual DB/Redis, should return 503
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_health_ready_error_contains_details(self, async_client: AsyncClient) -> None:
        """Test /api/health/ready error contains dependency info."""
        response = await async_client.get("/api/health/ready")
        data = response.json()

        assert "detail" in data
        assert "Not ready" in data["detail"]


# =============================================================================
# Version Endpoint Integration Tests
# =============================================================================


class TestVersionEndpoint:
    """Integration tests for version endpoint."""

    @pytest.mark.asyncio
    async def test_version_returns_200(self, async_client: AsyncClient) -> None:
        """Test /api/version returns 200."""
        response = await async_client.get("/api/version")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_version_response_structure(self, async_client: AsyncClient) -> None:
        """Test /api/version response structure."""
        response = await async_client.get("/api/version")
        data = response.json()

        assert "version" in data
        assert "environment" in data
        assert "python_version" in data

    @pytest.mark.asyncio
    async def test_version_format(self, async_client: AsyncClient) -> None:
        """Test version is in semver format."""
        response = await async_client.get("/api/version")
        data = response.json()

        version = data["version"]
        # Should be like "0.1.0"
        parts = version.split(".")
        assert len(parts) >= 2

    @pytest.mark.asyncio
    async def test_python_version_format(self, async_client: AsyncClient) -> None:
        """Test Python version is in correct format."""
        response = await async_client.get("/api/version")
        data = response.json()

        python_version = data["python_version"]
        # Should be like "3.11.0"
        parts = python_version.split(".")
        assert len(parts) >= 2
        assert parts[0].isdigit()


# =============================================================================
# Translation Endpoint Integration Tests
# =============================================================================


class TestTranslationEndpoints:
    """Integration tests for translation endpoints."""

    @pytest.mark.asyncio
    async def test_translate_endpoint_exists(self, async_client: AsyncClient) -> None:
        """Test /api/v1/translate endpoint exists."""
        response = await async_client.post(
            "/api/v1/translate",
            json={"text": "hello", "source_lang": "en", "target_lang": "zh"},
        )

        # Should return 501 (not implemented) or 200
        assert response.status_code in [200, 501]

    @pytest.mark.asyncio
    async def test_languages_endpoint(self, async_client: AsyncClient) -> None:
        """Test /api/v1/translate/languages endpoint."""
        response = await async_client.get("/api/v1/translate/languages")

        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert isinstance(data["languages"], list)

    @pytest.mark.asyncio
    async def test_languages_include_common_languages(self, async_client: AsyncClient) -> None:
        """Test languages list includes common languages."""
        response = await async_client.get("/api/v1/translate/languages")
        data = response.json()

        language_codes = [lang["code"] for lang in data["languages"]]
        assert "en" in language_codes
        assert "zh" in language_codes

    @pytest.mark.asyncio
    async def test_translate_batch_endpoint_exists(self, async_client: AsyncClient) -> None:
        """Test /api/v1/translate/batch endpoint exists."""
        response = await async_client.post(
            "/api/v1/translate/batch",
            json={
                "texts": ["hello", "world"],
                "source_lang": "en",
                "target_lang": "zh",
            },
        )

        # Should return 501 (not implemented) or 200
        assert response.status_code in [200, 501]


# =============================================================================
# Usage Endpoint Integration Tests
# =============================================================================


class TestUsageEndpoints:
    """Integration tests for usage endpoints."""

    @pytest.mark.asyncio
    async def test_usage_endpoint_exists(self, async_client: AsyncClient) -> None:
        """Test /api/v1/usage endpoint exists."""
        response = await async_client.get("/api/v1/usage")

        # Should return 501 (not implemented) or require auth
        assert response.status_code in [200, 401, 501]

    @pytest.mark.asyncio
    async def test_quota_endpoint_exists(self, async_client: AsyncClient) -> None:
        """Test /api/v1/usage/quota endpoint exists."""
        response = await async_client.get("/api/v1/usage/quota")

        # Should return 501 (not implemented) or require auth
        assert response.status_code in [200, 401, 501]


# =============================================================================
# Billing Endpoint Integration Tests
# =============================================================================


class TestBillingEndpoints:
    """Integration tests for billing endpoints."""

    @pytest.mark.asyncio
    async def test_checkout_endpoint_exists(self, async_client: AsyncClient) -> None:
        """Test /api/v1/billing/checkout endpoint exists."""
        response = await async_client.post(
            "/api/v1/billing/checkout",
            json={
                "plan": "basic",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        )

        # Should require auth or return 501
        assert response.status_code in [200, 401, 501]

    @pytest.mark.asyncio
    async def test_subscription_endpoint_exists(self, async_client: AsyncClient) -> None:
        """Test /api/v1/billing/subscription endpoint exists."""
        response = await async_client.get("/api/v1/billing/subscription")

        # Should require auth or return 501
        assert response.status_code in [200, 401, 501]


# =============================================================================
# Error Handling Integration Tests
# =============================================================================


class TestErrorHandling:
    """Integration tests for error handling."""

    @pytest.mark.asyncio
    async def test_404_for_unknown_endpoint(self, async_client: AsyncClient) -> None:
        """Test 404 for unknown endpoints."""
        response = await async_client.get("/api/v1/unknown")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_405_for_wrong_method(self, async_client: AsyncClient) -> None:
        """Test 405 for wrong HTTP method."""
        response = await async_client.delete("/api/health")

        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_422_for_invalid_json(self, async_client: AsyncClient) -> None:
        """Test 422 for invalid JSON."""
        response = await async_client.post(
            "/api/v1/translate",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


# =============================================================================
# CORS Integration Tests
# =============================================================================


class TestCORS:
    """Integration tests for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, async_client: AsyncClient) -> None:
        """Test CORS headers are present in response."""
        response = await async_client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should succeed
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_exposed_headers(self, async_client: AsyncClient) -> None:
        """Test that custom headers are exposed."""
        response = await async_client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"},
        )

        # Our custom headers should be in the response
        assert "X-Correlation-ID" in response.headers
        assert "X-Response-Time" in response.headers


# =============================================================================
# Content Type Tests
# =============================================================================


class TestContentTypes:
    """Integration tests for content type handling."""

    @pytest.mark.asyncio
    async def test_json_response_content_type(self, async_client: AsyncClient) -> None:
        """Test responses have correct content type."""
        response = await async_client.get("/api/health")

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    @pytest.mark.asyncio
    async def test_accepts_json_content_type(self, async_client: AsyncClient) -> None:
        """Test server accepts JSON content type."""
        response = await async_client.post(
            "/api/v1/translate",
            json={"text": "test", "source_lang": "en", "target_lang": "zh"},
            headers={"Content-Type": "application/json"},
        )

        # Should not reject based on content type
        assert response.status_code != 415


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Basic performance tests."""

    @pytest.mark.asyncio
    async def test_health_response_time(self, async_client: AsyncClient) -> None:
        """Test health endpoint responds within acceptable time."""
        import time

        start = time.perf_counter()
        response = await async_client.get("/api/health")
        elapsed = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        # Should respond in under 1 second
        assert elapsed < 1000

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self, async_client: AsyncClient) -> None:
        """Test multiple sequential requests are handled correctly."""
        for _i in range(5):
            response = await async_client.get("/api/health/live")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client: AsyncClient) -> None:
        """Test concurrent requests are handled correctly."""
        import asyncio

        async def make_request() -> int:
            response = await async_client.get("/api/health/live")
            return response.status_code

        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(status == 200 for status in results)
