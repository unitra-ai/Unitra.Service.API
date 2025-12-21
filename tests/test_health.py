"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Test health check returns 200 with correct response structure.

    Note: In test environment without DB/Redis, status will be unhealthy.
    We verify the response structure is correct.
    """
    response = await async_client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    # Verify response structure
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "components" in data

    # Verify components structure
    components = data["components"]
    assert "database" in components
    assert "redis" in components

    # Each component should have status
    for component in components.values():
        assert "status" in component
        assert component["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.asyncio
async def test_health_check_has_correlation_id(async_client: AsyncClient) -> None:
    """Test health check response includes correlation ID header."""
    response = await async_client.get("/api/health")
    assert "X-Correlation-ID" in response.headers
    assert "X-Response-Time" in response.headers


@pytest.mark.asyncio
async def test_liveness_probe(async_client: AsyncClient) -> None:
    """Test liveness probe returns quickly without dependency checks."""
    response = await async_client.get("/api/health/live")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe_without_deps(async_client: AsyncClient) -> None:
    """Test readiness probe returns 503 when dependencies unavailable."""
    response = await async_client.get("/api/health/ready")
    # Without initialized DB/Redis, readiness should fail
    assert response.status_code == 503

    data = response.json()
    assert "detail" in data
    assert "Not ready" in data["detail"]


@pytest.mark.asyncio
async def test_version_endpoint(async_client: AsyncClient) -> None:
    """Test version endpoint returns version info."""
    response = await async_client.get("/api/version")
    assert response.status_code == 200

    data = response.json()
    assert "version" in data
    assert "environment" in data
    assert "python_version" in data
