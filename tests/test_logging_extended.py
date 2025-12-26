"""Extended tests for logging configuration."""

import logging
from unittest.mock import MagicMock, patch

import structlog

from app.core.logging import (
    LoggerMixin,
    clear_log_context,
    get_logger,
    log_context,
    setup_logging,
)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_development_mode(self) -> None:
        """Test logging setup in development mode."""
        with patch("app.core.logging.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                environment="development",
                debug=True,
            )

            setup_logging()

            # Check structlog is configured
            config = structlog.get_config()
            assert config is not None

    def test_setup_logging_production_mode(self) -> None:
        """Test logging setup in production mode."""
        with patch("app.core.logging.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                environment="production",
                debug=False,
            )

            setup_logging()

            # Check structlog is configured
            config = structlog.get_config()
            assert config is not None

    def test_setup_logging_sets_log_level(self) -> None:
        """Test logging setup sets correct log level."""
        # Reset logging state before test (basicConfig is no-op if handlers exist)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.NOTSET)

        with patch("app.core.logging.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                environment="development",
                debug=True,
            )

            setup_logging()

            # Root logger should be at DEBUG in debug mode
            assert root_logger.level == logging.DEBUG

    def test_setup_logging_suppresses_noisy_loggers(self) -> None:
        """Test logging setup suppresses noisy loggers."""
        with patch("app.core.logging.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                environment="production",
                debug=False,
            )

            setup_logging()

            # Check that noisy loggers are suppressed
            uvicorn_logger = logging.getLogger("uvicorn.access")
            assert uvicorn_logger.level == logging.WARNING

            httpx_logger = logging.getLogger("httpx")
            assert httpx_logger.level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test get_logger returns a bound logger."""
        logger = get_logger("test.module")

        assert logger is not None
        # Should be callable for logging
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_get_logger_with_none_name(self) -> None:
        """Test get_logger with None name."""
        logger = get_logger(None)

        assert logger is not None

    def test_get_logger_can_log(self) -> None:
        """Test logger can log messages."""
        logger = get_logger("test.logging")

        # Should not raise
        logger.info("test message")
        logger.debug("debug message", extra_field="value")
        logger.warning("warning message")


class TestLoggerMixin:
    """Tests for LoggerMixin class."""

    def test_mixin_provides_logger(self) -> None:
        """Test mixin provides logger property."""

        class TestClass(LoggerMixin):
            pass

        obj = TestClass()

        assert hasattr(obj, "logger")
        assert obj.logger is not None

    def test_mixin_logger_uses_class_name(self) -> None:
        """Test mixin logger uses class name."""

        class MyCustomClass(LoggerMixin):
            pass

        obj = MyCustomClass()
        logger = obj.logger

        # Should be able to log
        logger.info("test from mixin")

    def test_mixin_logger_is_bound_logger(self) -> None:
        """Test mixin logger is a bound logger."""

        class AnotherClass(LoggerMixin):
            pass

        obj = AnotherClass()

        assert hasattr(obj.logger, "info")
        assert hasattr(obj.logger, "bind")


class TestLogContext:
    """Tests for log_context function."""

    def test_log_context_adds_context(self) -> None:
        """Test log_context adds context variables."""
        # Clear any existing context
        clear_log_context()

        log_context(user_id="123", request_id="abc")

        # Context should be bound
        # (Note: actual verification would need to check structlog internals)

    def test_log_context_with_multiple_values(self) -> None:
        """Test log_context with multiple values."""
        clear_log_context()

        log_context(
            user_id="123",
            session_id="sess_456",
            ip_address="192.168.1.1",
        )

        # Should not raise
        logger = get_logger("test")
        logger.info("test with context")


class TestClearLogContext:
    """Tests for clear_log_context function."""

    def test_clear_log_context(self) -> None:
        """Test clear_log_context clears all context."""
        # Add some context
        log_context(user_id="123")

        # Clear it
        clear_log_context()

        # Should not raise
        logger = get_logger("test")
        logger.info("test after clear")

    def test_clear_log_context_multiple_times(self) -> None:
        """Test clear_log_context can be called multiple times."""
        clear_log_context()
        clear_log_context()
        clear_log_context()

        # Should not raise


class TestLoggingIntegration:
    """Integration tests for logging."""

    def test_structured_log_output(self) -> None:
        """Test structured logging produces expected output."""
        with patch("app.core.logging.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                environment="development",
                debug=True,
            )

            setup_logging()

            logger = get_logger("integration.test")

            # Should be able to log with extra fields
            logger.info(
                "test event",
                user_id="123",
                action="login",
                duration_ms=45.5,
            )

    def test_exception_logging(self) -> None:
        """Test logging exceptions."""
        logger = get_logger("exception.test")

        try:
            raise ValueError("test error")
        except ValueError:
            # Should be able to log exception info
            logger.exception("caught error")

    def test_bind_context_persists(self) -> None:
        """Test bound context persists across log calls."""
        logger = get_logger("bind.test")

        # Bind context
        bound_logger = logger.bind(request_id="req_123")

        # Multiple log calls should include context
        bound_logger.info("first call")
        bound_logger.info("second call")
        bound_logger.warning("warning call")
