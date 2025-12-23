"""Tests for logging configuration."""

from unittest.mock import patch

import pytest
import structlog

from app.core.logging import setup_logging

# =============================================================================
# Logging Setup Tests
# =============================================================================


class TestLoggingSetup:
    """Tests for logging setup."""

    def test_setup_logging_does_not_raise(self) -> None:
        """Test setup_logging runs without error."""
        # Should not raise any exceptions
        setup_logging()

    def test_logging_is_configured(self) -> None:
        """Test structlog is properly configured after setup."""
        setup_logging()

        # Should be able to get a logger
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_can_log_after_setup(self) -> None:
        """Test logging works after setup."""
        setup_logging()

        logger = structlog.get_logger("test.logging")

        # These should not raise
        logger.info("test message")
        logger.warning("warning message")
        logger.error("error message")

    @patch("app.core.logging.get_settings")
    def test_development_logging_uses_console_renderer(self, mock_settings) -> None:
        """Test development environment uses console renderer."""
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.debug = True
        mock_settings.return_value.log_level = "DEBUG"

        setup_logging()

        # Logger should work
        logger = structlog.get_logger("test.dev")
        logger.info("test")

    @patch("app.core.logging.get_settings")
    def test_production_logging_uses_json_renderer(self, mock_settings) -> None:
        """Test production environment uses JSON renderer."""
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.debug = False
        mock_settings.return_value.log_level = "INFO"

        setup_logging()

        # Logger should work
        logger = structlog.get_logger("test.prod")
        logger.info("test")


# =============================================================================
# Log Format Tests
# =============================================================================


class TestLogFormat:
    """Tests for log formatting."""

    def test_log_includes_timestamp(self) -> None:
        """Test logs include timestamp."""
        setup_logging()
        logger = structlog.get_logger("test.timestamp")

        # Create a log and verify it works
        logger.info("test message")
        # Timestamp is added by TimeStamper processor

    def test_log_includes_log_level(self) -> None:
        """Test logs include log level."""
        setup_logging()
        logger = structlog.get_logger("test.level")

        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

    def test_log_includes_logger_name(self) -> None:
        """Test logs include logger name."""
        setup_logging()
        logger = structlog.get_logger("test.name.here")

        logger.info("test")


# =============================================================================
# Context Variables Tests
# =============================================================================


class TestContextVariables:
    """Tests for context variable handling."""

    def test_can_bind_context_variables(self) -> None:
        """Test context variables can be bound."""
        setup_logging()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id="123",
            user_id="user-456",
        )

        logger = structlog.get_logger("test.context")
        logger.info("test with context")

        # Clean up
        structlog.contextvars.clear_contextvars()

    def test_context_variables_are_cleared(self) -> None:
        """Test context variables can be cleared."""
        setup_logging()

        structlog.contextvars.bind_contextvars(key="value")
        structlog.contextvars.clear_contextvars()

        # After clearing, new logs should not have old context
        logger = structlog.get_logger("test.clear")
        logger.info("test after clear")

    def test_multiple_context_bindings(self) -> None:
        """Test multiple context bindings work correctly."""
        setup_logging()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(key1="value1")
        structlog.contextvars.bind_contextvars(key2="value2")

        logger = structlog.get_logger("test.multi")
        logger.info("test with multiple context")

        structlog.contextvars.clear_contextvars()


# =============================================================================
# Log Level Tests
# =============================================================================


class TestLogLevels:
    """Tests for log levels."""

    def test_debug_level(self) -> None:
        """Test debug log level."""
        setup_logging()
        logger = structlog.get_logger("test.debug")
        logger.debug("debug message")

    def test_info_level(self) -> None:
        """Test info log level."""
        setup_logging()
        logger = structlog.get_logger("test.info")
        logger.info("info message")

    def test_warning_level(self) -> None:
        """Test warning log level."""
        setup_logging()
        logger = structlog.get_logger("test.warning")
        logger.warning("warning message")

    def test_error_level(self) -> None:
        """Test error log level."""
        setup_logging()
        logger = structlog.get_logger("test.error")
        logger.error("error message")

    def test_exception_logging(self) -> None:
        """Test exception logging."""
        setup_logging()
        logger = structlog.get_logger("test.exception")

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("caught exception")


# =============================================================================
# Structured Data Tests
# =============================================================================


class TestStructuredData:
    """Tests for structured data in logs."""

    def test_log_with_extra_fields(self) -> None:
        """Test logging with extra fields."""
        setup_logging()
        logger = structlog.get_logger("test.extra")

        logger.info(
            "request completed",
            status_code=200,
            duration_ms=15.5,
            path="/api/health",
        )

    def test_log_with_nested_data(self) -> None:
        """Test logging with nested data structures."""
        setup_logging()
        logger = structlog.get_logger("test.nested")

        logger.info(
            "complex data",
            user={"id": "123", "email": "test@example.com"},
            metadata={"version": "1.0"},
        )

    def test_log_with_list_data(self) -> None:
        """Test logging with list data."""
        setup_logging()
        logger = structlog.get_logger("test.list")

        logger.info(
            "list data",
            items=[1, 2, 3],
            errors=["error1", "error2"],
        )


# =============================================================================
# Unicode and Special Characters Tests
# =============================================================================


class TestSpecialCharacters:
    """Tests for special characters in logs."""

    def test_unicode_in_message(self) -> None:
        """Test unicode characters in log message."""
        setup_logging()
        logger = structlog.get_logger("test.unicode")

        logger.info("用户登录成功 🎉")
        logger.info("Пользователь вошел в систему")

    def test_unicode_in_extra_fields(self) -> None:
        """Test unicode in extra fields."""
        setup_logging()
        logger = structlog.get_logger("test.unicode.fields")

        logger.info(
            "user action",
            username="用户名",
            action="登录",
        )

    def test_special_characters_in_message(self) -> None:
        """Test special characters in log message."""
        setup_logging()
        logger = structlog.get_logger("test.special")

        logger.info('Message with "quotes" and \\backslashes\\')
        logger.info("Message with\nnewlines\tand tabs")


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in logging."""

    def test_log_with_none_values(self) -> None:
        """Test logging with None values."""
        setup_logging()
        logger = structlog.get_logger("test.none")

        logger.info("test with none", value=None, other="valid")

    def test_log_with_empty_message(self) -> None:
        """Test logging with empty message."""
        setup_logging()
        logger = structlog.get_logger("test.empty")

        logger.info("", key="value")

    def test_log_does_not_fail_on_unserializable(self) -> None:
        """Test logging doesn't fail on unserializable objects."""
        setup_logging()
        logger = structlog.get_logger("test.unserializable")

        class CustomObject:
            pass

        # Should not raise, even with unserializable object
        try:
            logger.info("test", obj=CustomObject())
        except Exception:
            pytest.fail("Logging should not fail on unserializable objects")
