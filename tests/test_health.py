"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Test health check returns 200 with correct response."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_check_has_request_id(async_client: AsyncClient) -> None:
    """Test health check response includes request ID header."""
    response = await async_client.get("/api/health")
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers
