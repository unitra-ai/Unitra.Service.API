"""Custom middleware."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import RateLimitError
from app.db.redis import RedisClient


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging with timing and correlation IDs.

    Features:
    - Generates or uses existing correlation ID
    - Binds context for structured logging
    - Times request processing
    - Adds response headers
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            str(uuid.uuid4()),
        )
        request.state.correlation_id = correlation_id

        # Bind context for all logs in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        # Get logger after binding context
        logger = structlog.get_logger("app.middleware")

        # Record start time
        start_time = time.perf_counter()

        # Log request start
        logger.info("request_started")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log request completion
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""

    # Paths to skip rate limiting
    SKIP_PATHS = {
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/api/version",
        "/api/docs",
        "/api/openapi.json",
    }

    def __init__(
        self,
        app: object,
        redis_client: RedisClient,
        default_limit: int = 100,
        window: int = 60,
    ) -> None:
        super().__init__(app)
        self.redis = redis_client
        self.default_limit = default_limit
        self.window = window
        self.logger = structlog.get_logger("app.middleware.ratelimit")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        # Skip rate limiting for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Get user identifier (user_id if authenticated, otherwise IP)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # Use client IP for unauthenticated requests
            user_id = request.client.host if request.client else "unknown"

        # Check rate limit
        try:
            allowed, remaining = await self.redis.check_rate_limit(
                user_id=str(user_id),
                endpoint=request.url.path,
                limit=self.default_limit,
                window=self.window,
            )
        except Exception as e:
            # If Redis fails, allow the request but log the error
            self.logger.warning(
                "rate_limit_check_failed",
                error=str(e),
                user_id=str(user_id),
            )
            return await call_next(request)

        if not allowed:
            ttl = await self.redis.get_rate_limit_ttl(str(user_id), request.url.path)
            self.logger.warning(
                "rate_limit_exceeded",
                user_id=str(user_id),
                endpoint=request.url.path,
            )
            raise RateLimitError(retry_after=max(ttl, 1))

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(self.window)

        return response
