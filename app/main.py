"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.redis import close_redis, init_redis
from app.db.session import close_db, init_db

# Setup structured logging before anything else
setup_logging()

# Get logger after setup
logger = structlog.get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    settings = get_settings()

    # Startup
    logger.info(
        "application_starting",
        version=settings.app_version,
        environment=settings.environment,
    )

    await init_db()
    logger.info("database_initialized")

    await init_redis()
    logger.info("redis_initialized")

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_stopping")

    await close_db()
    logger.info("database_closed")

    await close_redis()
    logger.info("redis_closed")

    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Unitra Translation API - AI-powered translation platform",
        openapi_url="/api/openapi.json" if settings.debug else None,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Response-Time", "X-RateLimit-*"],
    )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Include API router
    app.include_router(api_router, prefix="/api")

    return app


# Create the app instance
app = create_app()
