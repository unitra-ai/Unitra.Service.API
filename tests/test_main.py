"""Tests for main application module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from app.main import app, create_app, lifespan


class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test create_app returns FastAPI instance."""
        assert isinstance(app, FastAPI)

    def test_app_has_title(self) -> None:
        """Test app has correct title."""
        assert app.title == "Unitra API"

    def test_app_has_version(self) -> None:
        """Test app has version set."""
        assert app.version is not None

    def test_app_includes_api_router(self) -> None:
        """Test app includes API router."""
        routes = [r.path for r in app.routes]
        # Check that some API routes exist
        assert any("/api" in route for route in routes)

    def test_app_has_cors_middleware(self) -> None:
        """Test app has CORS middleware configured."""
        # CORS is handled by Starlette's CORSMiddleware
        assert any("CORSMiddleware" in str(m) for m in app.user_middleware)

    def test_debug_mode_shows_docs(self) -> None:
        """Test debug mode enables docs."""
        with patch("app.main.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                app_name="Test",
                app_version="1.0.0",
                debug=True,
                cors_origins=["http://localhost:3000"],
                environment="test",
            )

            test_app = create_app()

            assert test_app.docs_url == "/api/docs"
            assert test_app.redoc_url == "/api/redoc"
            assert test_app.openapi_url == "/api/openapi.json"

    def test_production_mode_hides_docs(self) -> None:
        """Test production mode disables docs."""
        with patch("app.main.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                app_name="Test",
                app_version="1.0.0",
                debug=False,
                cors_origins=["http://localhost:3000"],
                environment="production",
            )

            test_app = create_app()

            assert test_app.docs_url is None
            assert test_app.redoc_url is None
            assert test_app.openapi_url is None


class TestLifespan:
    """Tests for application lifespan."""

    @pytest.mark.asyncio
    async def test_lifespan_initializes_db_and_redis(self) -> None:
        """Test lifespan initializes database and Redis."""
        mock_app = MagicMock(spec=FastAPI)

        with (
            patch("app.main.init_db", new_callable=AsyncMock) as mock_init_db,
            patch("app.main.init_redis", new_callable=AsyncMock) as mock_init_redis,
            patch("app.main.close_db", new_callable=AsyncMock) as mock_close_db,
            patch("app.main.close_redis", new_callable=AsyncMock) as mock_close_redis,
        ):
            async with lifespan(mock_app):
                # During lifespan, DB and Redis should be initialized
                mock_init_db.assert_called_once()
                mock_init_redis.assert_called_once()

            # After lifespan exits, should close connections
            mock_close_db.assert_called_once()
            mock_close_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_logs_startup(self) -> None:
        """Test lifespan logs startup events."""
        mock_app = MagicMock(spec=FastAPI)

        with (
            patch("app.main.init_db", new_callable=AsyncMock),
            patch("app.main.init_redis", new_callable=AsyncMock),
            patch("app.main.close_db", new_callable=AsyncMock),
            patch("app.main.close_redis", new_callable=AsyncMock),
            patch("app.main.logger") as mock_logger,
        ):
            async with lifespan(mock_app):
                pass

            # Check logging calls
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("application_starting" in c for c in calls)
            assert any("application_started" in c for c in calls)

    @pytest.mark.asyncio
    async def test_lifespan_logs_shutdown(self) -> None:
        """Test lifespan logs shutdown events."""
        mock_app = MagicMock(spec=FastAPI)

        with (
            patch("app.main.init_db", new_callable=AsyncMock),
            patch("app.main.init_redis", new_callable=AsyncMock),
            patch("app.main.close_db", new_callable=AsyncMock),
            patch("app.main.close_redis", new_callable=AsyncMock),
            patch("app.main.logger") as mock_logger,
        ):
            async with lifespan(mock_app):
                pass

            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("application_stopping" in c for c in calls)
            assert any("application_stopped" in c for c in calls)


class TestAppConfiguration:
    """Tests for app configuration."""

    def test_exception_handlers_registered(self) -> None:
        """Test exception handlers are registered."""
        # Check that we have exception handlers
        assert len(app.exception_handlers) > 0

    def test_request_logging_middleware_added(self) -> None:
        """Test request logging middleware is added."""
        middleware_names = [str(m) for m in app.user_middleware]
        assert any("RequestLogging" in name for name in middleware_names)
