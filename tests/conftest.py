"""Pytest fixtures and configuration for testing."""

import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app


# =============================================================================
# Environment Setup
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def set_test_env() -> Generator[None, None, None]:
    """Set environment variables for testing."""
    original_env = os.environ.copy()

    os.environ["ENVIRONMENT"] = "test"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-not-for-production"
    os.environ["DEBUG"] = "true"

    yield

    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# Settings Fixtures
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="test",
        debug=True,
        secret_key="test-secret-key-for-testing-only-not-for-production",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
def mock_settings(test_settings: Settings) -> Generator[Settings, None, None]:
    """Mock get_settings to return test settings."""
    with patch("app.config.get_settings", return_value=test_settings):
        yield test_settings


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create a synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def test_app() -> FastAPI:
    """Get the FastAPI application instance."""
    return app


# =============================================================================
# Mock Database Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_db_result() -> MagicMock:
    """Create a mock database result."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return result


# =============================================================================
# Mock Redis Fixtures
# =============================================================================


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=60)
    redis.check_rate_limit = AsyncMock(return_value=(True, 99))
    redis.get_rate_limit_ttl = AsyncMock(return_value=60)
    return redis


# =============================================================================
# Authentication Fixtures
# =============================================================================


@pytest.fixture
def valid_access_token() -> str:
    """Generate a valid access token for testing."""
    from app.core.security import create_access_token

    return create_access_token(
        subject="test-user-id",
        additional_claims={"email": "test@example.com"},
    )


@pytest.fixture
def expired_access_token() -> str:
    """Generate an expired access token for testing."""
    from datetime import timedelta

    from app.core.security import create_access_token

    return create_access_token(
        subject="test-user-id",
        expires_delta=timedelta(seconds=-1),
    )


@pytest.fixture
def auth_headers(valid_access_token: str) -> dict[str, str]:
    """Create authorization headers with valid token."""
    return {"Authorization": f"Bearer {valid_access_token}"}


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def test_user_id() -> str:
    """Test user ID."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def test_user_email() -> str:
    """Test user email."""
    return "test@example.com"


@pytest.fixture
def mock_user(test_user_id: str, test_user_email: str) -> MagicMock:
    """Create a mock user object."""
    user = MagicMock()
    user.id = test_user_id
    user.email = test_user_email
    user.is_active = True
    user.is_verified = True
    user.tier = "FREE"
    user.hashed_password = "hashed_password"
    return user


# =============================================================================
# Request Fixtures
# =============================================================================


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock FastAPI request."""
    request = MagicMock()
    request.url.path = "/api/test"
    request.method = "GET"
    request.headers = {}
    request.client.host = "127.0.0.1"
    request.state = MagicMock()
    return request


# =============================================================================
# Utility Functions
# =============================================================================


def create_mock_response(status_code: int = 200) -> MagicMock:
    """Create a mock response object."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    return response


async def async_return(value):
    """Helper to create async return value."""
    return value
