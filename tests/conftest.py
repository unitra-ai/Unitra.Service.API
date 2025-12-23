"""Pytest fixtures and configuration for testing."""

import os
from collections.abc import AsyncGenerator, Generator
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Import all models to register them with SQLAlchemy metadata
# This ensures relationships are properly resolved when creating tables
from app.auth.models import User  # noqa: F401
from app.config import Settings
from app.db.base import Base
from app.main import app
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.usage import UsageLog  # noqa: F401

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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

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
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        jwt_lifetime_seconds=3600,
        password_reset_token_lifetime_seconds=3600,
        verification_token_lifetime_seconds=86400,
    )


@pytest.fixture
def mock_settings(test_settings: Settings) -> Generator[Settings, None, None]:
    """Mock get_settings to return test settings."""
    with patch("app.config.get_settings", return_value=test_settings):
        yield test_settings


# =============================================================================
# Database Fixtures for Testing
# =============================================================================


@pytest_asyncio.fixture
async def test_db_engine():
    """Create a test database engine using SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create a synchronous test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(test_db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with test database.

    This fixture:
    1. Creates an in-memory SQLite database with all tables
    2. Overrides the get_db_session dependency to use the test database
    3. Mocks Redis client for testing
    4. Provides an async HTTP client for making requests
    """
    from app.db.redis import RedisClient, get_redis
    from app.db.session import get_db_session

    # Create async session factory for test database
    test_session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Create a mock Redis client for testing
    mock_redis = MagicMock(spec=RedisClient)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.blacklist_token = AsyncMock()
    mock_redis.is_token_blacklisted = AsyncMock(return_value=False)
    mock_redis.delete_session = AsyncMock()
    mock_redis.get_session = AsyncMock(return_value=None)
    mock_redis.set_session = AsyncMock()
    mock_redis.check_rate_limit = AsyncMock(return_value=(True, 99))
    mock_redis.get_rate_limit_ttl = AsyncMock(return_value=60)

    def override_get_redis() -> RedisClient:
        return mock_redis

    # Override the dependencies
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    # Clear the override after tests
    app.dependency_overrides.clear()


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
# Authentication Fixtures (FastAPI-Users)
# =============================================================================


@pytest.fixture
def valid_access_token() -> str:
    """Generate a valid access token for testing."""
    from app.core.security import create_access_token

    return create_access_token(data={"sub": "test-user-id"})


@pytest.fixture
def expired_access_token() -> str:
    """Generate an expired access token for testing."""
    from app.core.security import create_access_token

    return create_access_token(
        data={"sub": "test-user-id"},
        expires_delta=timedelta(seconds=-1),
    )


@pytest.fixture
def auth_headers(valid_access_token: str) -> dict[str, str]:
    """Create authorization headers with valid token."""
    return {"Authorization": f"Bearer {valid_access_token}"}


def get_auth_headers_for_user(user_id: str) -> dict[str, str]:
    """Create authorization headers for a specific user."""
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": user_id})
    return {"Authorization": f"Bearer {token}"}


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
def test_user_password() -> str:
    """Test user password."""
    return "testpassword123"


@pytest.fixture
def mock_user(test_user_id: str, test_user_email: str) -> MagicMock:
    """Create a mock user object."""
    user = MagicMock()
    user.id = test_user_id
    user.email = test_user_email
    user.is_active = True
    user.is_verified = False
    user.is_superuser = False
    user.tier = "free"
    user.hashed_password = "hashed_password"
    user.translation_minutes_used = 0
    user.translation_minutes_limit = 60
    user.login_count = 0
    user.last_login_at = None
    return user


@pytest.fixture
def verified_mock_user(mock_user: MagicMock) -> MagicMock:
    """Create a mock verified user."""
    mock_user.is_verified = True
    return mock_user


@pytest.fixture
def superuser_mock_user(verified_mock_user: MagicMock) -> MagicMock:
    """Create a mock superuser."""
    verified_mock_user.is_superuser = True
    return verified_mock_user


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


# =============================================================================
# Factory Fixtures for Auth Testing
# =============================================================================


@pytest.fixture
def user_data_factory():
    """Factory for creating user registration data."""

    def _create_user_data(
        email: str | None = None,
        password: str = "testpassword123",
        **kwargs,
    ) -> dict:
        return {
            "email": email or f"user_{uuid4().hex[:8]}@example.com",
            "password": password,
            **kwargs,
        }

    return _create_user_data


@pytest_asyncio.fixture
async def registered_user(async_client: AsyncClient) -> dict:
    """Create and register a test user, returning their credentials."""
    email = f"testuser_{uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201

    return {
        "email": email,
        "password": password,
        "user": response.json(),
    }


@pytest_asyncio.fixture
async def registered_user_token(
    async_client: AsyncClient,
    registered_user: dict,
) -> str:
    """Get an access token for the registered user."""
    response = await async_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200

    return response.json()["access_token"]
