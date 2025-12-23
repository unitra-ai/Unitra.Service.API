"""Tests for database session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.session import (
    close_db,
    get_db_session,
    init_db,
)


class TestDatabaseSession:
    """Tests for database session functions."""

    @pytest.mark.asyncio
    async def test_init_db_creates_engine_and_factory(self) -> None:
        """Test init_db creates engine and session factory."""
        import app.db.session as session_module

        with patch("app.db.session.create_async_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            with patch("app.db.session.async_sessionmaker") as mock_sessionmaker:
                mock_factory = MagicMock()
                mock_sessionmaker.return_value = mock_factory

                await init_db()

                mock_create_engine.assert_called_once()
                mock_sessionmaker.assert_called_once()
                assert session_module._engine is not None
                assert session_module._async_session_factory is not None

    @pytest.mark.asyncio
    async def test_close_db_disposes_engine(self) -> None:
        """Test close_db disposes engine."""
        import app.db.session as session_module

        mock_engine = AsyncMock()
        session_module._engine = mock_engine

        await close_db()

        mock_engine.dispose.assert_called_once()
        assert session_module._engine is None

    @pytest.mark.asyncio
    async def test_close_db_handles_none_engine(self) -> None:
        """Test close_db handles None engine gracefully."""
        import app.db.session as session_module

        session_module._engine = None

        await close_db()  # Should not raise

    @pytest.mark.asyncio
    async def test_get_db_session_raises_when_not_initialized(self) -> None:
        """Test get_db_session raises error when not initialized."""
        import app.db.session as session_module

        session_module._async_session_factory = None

        with pytest.raises(RuntimeError, match="Database not initialized"):
            async for _ in get_db_session():
                pass

    @pytest.mark.asyncio
    async def test_get_db_session_yields_and_commits(self) -> None:
        """Test get_db_session yields session and commits."""
        from contextlib import asynccontextmanager

        import app.db.session as session_module

        mock_session = AsyncMock()

        # Create a real async context manager that properly wraps our mock
        @asynccontextmanager
        async def mock_context_manager():
            yield mock_session

        mock_factory = MagicMock(side_effect=lambda: mock_context_manager())
        session_module._async_session_factory = mock_factory

        async for session in get_db_session():
            assert session == mock_session

        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_session_rollbacks_on_exception(self) -> None:
        """Test get_db_session rollbacks on exception.

        Note: We must use athrow() to properly simulate how FastAPI throws
        exceptions into dependency generators. A simple 'raise' in async for
        body doesn't throw into the generator - it just propagates out.
        """
        from contextlib import asynccontextmanager

        import app.db.session as session_module

        mock_session = AsyncMock()

        # Create a real async context manager that properly wraps our mock
        @asynccontextmanager
        async def mock_context_manager():
            yield mock_session

        mock_factory = MagicMock(side_effect=lambda: mock_context_manager())
        session_module._async_session_factory = mock_factory

        # Get the generator and manually control it
        gen = get_db_session()

        # Start the generator and get the session
        session = await gen.__anext__()
        assert session == mock_session

        # Throw an exception INTO the generator (like FastAPI does)
        with pytest.raises(ValueError):
            await gen.athrow(ValueError("Test error"))

        # The rollback should have been called due to the exception
        mock_session.rollback.assert_awaited_once()
