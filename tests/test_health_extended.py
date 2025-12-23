"""Extended tests for health check endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.health import (
    ComponentHealth,
    HealthStatus,
    SimpleHealthResponse,
    VersionResponse,
    get_optional_db,
    get_optional_redis,
    router,
)


class TestHealthModels:
    """Tests for health response models."""

    def test_health_status_enum_values(self) -> None:
        """Test HealthStatus enum has correct values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"

    def test_component_health_basic(self) -> None:
        """Test ComponentHealth model creation."""
        component = ComponentHealth(status=HealthStatus.HEALTHY)
        assert component.status == HealthStatus.HEALTHY
        assert component.latency_ms is None
        assert component.message is None

    def test_component_health_with_latency(self) -> None:
        """Test ComponentHealth with latency."""
        component = ComponentHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=5.23,
        )
        assert component.latency_ms == 5.23

    def test_component_health_with_message(self) -> None:
        """Test ComponentHealth with message."""
        component = ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message="Connection failed",
        )
        assert component.message == "Connection failed"

    def test_simple_health_response(self) -> None:
        """Test SimpleHealthResponse model."""
        response = SimpleHealthResponse(status="alive")
        assert response.status == "alive"

    def test_version_response(self) -> None:
        """Test VersionResponse model."""
        response = VersionResponse(
            version="1.0.0",
            environment="test",
            python_version="3.10.0",
            commit_sha="abc123",
        )
        assert response.version == "1.0.0"
        assert response.environment == "test"
        assert response.python_version == "3.10.0"
        assert response.commit_sha == "abc123"

    def test_version_response_optional_sha(self) -> None:
        """Test VersionResponse without commit SHA."""
        response = VersionResponse(
            version="1.0.0",
            environment="test",
            python_version="3.10.0",
        )
        assert response.commit_sha is None


class TestOptionalDependencies:
    """Tests for optional dependency functions."""

    @pytest.mark.asyncio
    async def test_get_optional_db_returns_none_on_exception(self) -> None:
        """Test get_optional_db returns None when database fails."""
        with patch(
            "app.api.v1.health.get_db_session",
            side_effect=RuntimeError("Database not initialized"),
        ):
            result = await get_optional_db()
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_redis_returns_none_on_exception(self) -> None:
        """Test get_optional_redis returns None when Redis fails."""
        with patch(
            "app.api.v1.health.get_redis",
            side_effect=RuntimeError("Redis not initialized"),
        ):
            result = await get_optional_redis()
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_redis_returns_client(self) -> None:
        """Test get_optional_redis returns client when available."""
        mock_client = MagicMock()
        with patch("app.api.v1.health.get_redis", return_value=mock_client):
            result = await get_optional_redis()
            assert result == mock_client


class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints."""

    @pytest.fixture
    def app_with_health(self) -> FastAPI:
        """Create app with health router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_health_with_db_not_initialized(self, app_with_health: FastAPI) -> None:
        """Test health endpoint when DB is not initialized."""
        app = app_with_health

        # Override dependencies to simulate not initialized
        app.dependency_overrides[get_optional_db] = lambda: None
        app.dependency_overrides[get_optional_redis] = lambda: None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"]["status"] == "unhealthy"
        assert data["components"]["redis"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_with_db_error(self, app_with_health: FastAPI) -> None:
        """Test health endpoint when DB query fails."""
        app = app_with_health

        # Mock DB that fails on query
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB query failed"))

        async def mock_get_db():
            return mock_session

        app.dependency_overrides[get_optional_db] = mock_get_db
        app.dependency_overrides[get_optional_redis] = lambda: None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"]["status"] == "unhealthy"
        assert "DB query failed" in data["components"]["database"]["message"]

    @pytest.mark.asyncio
    async def test_health_with_redis_error(self, app_with_health: FastAPI) -> None:
        """Test health endpoint when Redis ping fails."""
        app = app_with_health

        # Mock successful DB
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Mock Redis that fails on ping
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Redis connection failed"))

        async def mock_get_db():
            return mock_session

        async def mock_get_redis():
            return mock_redis

        app.dependency_overrides[get_optional_db] = mock_get_db
        app.dependency_overrides[get_optional_redis] = mock_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        # DB is healthy, Redis is unhealthy -> degraded
        assert data["status"] == "degraded"
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["redis"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_all_healthy(self, app_with_health: FastAPI) -> None:
        """Test health endpoint when all components are healthy."""
        app = app_with_health

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        async def mock_get_db():
            return mock_session

        async def mock_get_redis():
            return mock_redis

        app.dependency_overrides[get_optional_db] = mock_get_db
        app.dependency_overrides[get_optional_redis] = mock_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["redis"]["status"] == "healthy"
        assert "latency_ms" in data["components"]["database"]
        assert "latency_ms" in data["components"]["redis"]

    @pytest.mark.asyncio
    async def test_readiness_returns_503_when_not_ready(self, app_with_health: FastAPI) -> None:
        """Test readiness probe returns 503 when not ready."""
        app = app_with_health

        app.dependency_overrides[get_optional_db] = lambda: None
        app.dependency_overrides[get_optional_redis] = lambda: None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_readiness_returns_503_on_db_error(self, app_with_health: FastAPI) -> None:
        """Test readiness probe returns 503 when DB fails."""
        app = app_with_health

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))

        async def mock_get_db():
            return mock_session

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        async def mock_get_redis():
            return mock_redis

        app.dependency_overrides[get_optional_db] = mock_get_db
        app.dependency_overrides[get_optional_redis] = mock_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 503
        assert "Database" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_readiness_returns_503_on_redis_error(self, app_with_health: FastAPI) -> None:
        """Test readiness probe returns 503 when Redis fails."""
        app = app_with_health

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        async def mock_get_db():
            return mock_session

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Redis error"))

        async def mock_get_redis():
            return mock_redis

        app.dependency_overrides[get_optional_db] = mock_get_db
        app.dependency_overrides[get_optional_redis] = mock_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 503
        assert "Redis" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_readiness_returns_200_when_ready(self, app_with_health: FastAPI) -> None:
        """Test readiness probe returns 200 when all components ready."""
        app = app_with_health

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        async def mock_get_db():
            return mock_session

        async def mock_get_redis():
            return mock_redis

        app.dependency_overrides[get_optional_db] = mock_get_db
        app.dependency_overrides[get_optional_redis] = mock_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    @pytest.mark.asyncio
    async def test_version_endpoint(self, app_with_health: FastAPI) -> None:
        """Test version endpoint returns correct info."""
        app = app_with_health

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data

    @pytest.mark.asyncio
    async def test_version_with_commit_sha(self, app_with_health: FastAPI) -> None:
        """Test version endpoint includes commit SHA when available."""
        app = app_with_health

        with patch.dict("os.environ", {"GIT_COMMIT_SHA": "abc123def456"}):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/version")

        assert response.status_code == 200
        data = response.json()
        assert data["commit_sha"] == "abc123def456"
