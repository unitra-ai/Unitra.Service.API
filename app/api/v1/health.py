"""Health check endpoints."""

import os
import sys
import time
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.redis import RedisClient, get_redis
from app.db.session import get_db_session

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status for a single component."""

    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """Comprehensive health check response."""

    status: HealthStatus
    version: str
    environment: str
    timestamp: datetime
    components: dict[str, ComponentHealth]


class SimpleHealthResponse(BaseModel):
    """Simple health response for probes."""

    status: str


class VersionResponse(BaseModel):
    """Version information response."""

    version: str
    environment: str
    python_version: str
    commit_sha: str | None = None


# =============================================================================
# Optional Dependencies (for health checks that should work even when deps fail)
# =============================================================================


async def get_optional_db() -> AsyncSession | None:
    """Get database session, returning None if not available."""
    try:
        async for session in get_db_session():
            return session
    except Exception:
        return None
    return None


async def get_optional_redis() -> RedisClient | None:
    """Get Redis client, returning None if not available."""
    try:
        return get_redis()
    except Exception:
        return None


# =============================================================================
# Health Check Endpoints
# =============================================================================


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession | None = Depends(get_optional_db),
    redis: RedisClient | None = Depends(get_optional_redis),
) -> HealthResponse:
    """Comprehensive health check endpoint.

    Checks:
    - Database connectivity and latency
    - Redis connectivity and latency

    Returns component-level health status.
    Works even when dependencies are not initialized (reports them as unhealthy).
    """
    settings = get_settings()
    components: dict[str, ComponentHealth] = {}
    overall_status = HealthStatus.HEALTHY

    # Check database
    if db is None:
        components["database"] = ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message="Database not initialized",
        )
        overall_status = HealthStatus.UNHEALTHY
    else:
        try:
            start = time.perf_counter()
            await db.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000

            components["database"] = ComponentHealth(
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            components["database"] = ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
            overall_status = HealthStatus.UNHEALTHY

    # Check Redis
    if redis is None:
        components["redis"] = ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message="Redis not initialized",
        )
        # Redis failure = degraded (caching, not critical for basic operation)
        if overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
    else:
        try:
            start = time.perf_counter()
            await redis.ping()
            latency = (time.perf_counter() - start) * 1000

            components["redis"] = ComponentHealth(
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            components["redis"] = ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        components=components,
    )


@router.get("/health/live", response_model=SimpleHealthResponse)
async def liveness_probe() -> SimpleHealthResponse:
    """Kubernetes liveness probe.

    Returns 200 if the application is running.
    This is a fast check that doesn't verify dependencies.
    """
    return SimpleHealthResponse(status="alive")


@router.get("/health/ready", response_model=SimpleHealthResponse)
async def readiness_probe(
    db: AsyncSession | None = Depends(get_optional_db),
    redis: RedisClient | None = Depends(get_optional_redis),
) -> SimpleHealthResponse:
    """Kubernetes readiness probe.

    Returns 200 if the application can accept traffic.
    Checks that all critical dependencies are available.
    """
    errors: list[str] = []

    # Check database
    if db is None:
        errors.append("Database not initialized")
    else:
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            errors.append(f"Database: {e}")

    # Check Redis
    if redis is None:
        errors.append("Redis not initialized")
    else:
        try:
            await redis.ping()
        except Exception as e:
            errors.append(f"Redis: {e}")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Not ready: {'; '.join(errors)}",
        )

    return SimpleHealthResponse(status="ready")


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    """Get application version information."""
    settings = get_settings()

    return VersionResponse(
        version=settings.app_version,
        environment=settings.environment,
        python_version=sys.version.split()[0],
        commit_sha=os.environ.get("GIT_COMMIT_SHA"),
    )
