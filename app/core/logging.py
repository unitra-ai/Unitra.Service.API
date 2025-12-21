"""Structured logging configuration with structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import get_settings


def setup_logging() -> None:
    """Configure structured logging with structlog.

    In development: Pretty console output with colors
    In production: JSON output for log aggregation
    """
    settings = get_settings()

    # Shared processors for all outputs
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "development":
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # JSON output for production (for log aggregation)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        A bound structlog logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add a logger to a class."""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger bound to this class."""
        return get_logger(self.__class__.__name__)


def log_context(**kwargs: Any) -> None:
    """Add context to all subsequent log messages in this request.

    Usage:
        log_context(user_id="123", request_id="abc")
        logger.info("processing")  # Will include user_id and request_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()
