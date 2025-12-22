"""Authentication routers for FastAPI-Users."""

from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import (
    auth_backend,
    current_user,
    current_verified_user,
    fastapi_users,
)
from app.auth.models import User
from app.auth.schemas import (
    AuthHealthResponse,
    TierUpgradeRequest,
    TierUpgradeResponse,
    UsageStatistics,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.config import get_settings
from app.db.session import get_db_session

logger = structlog.get_logger("app.auth.router")
settings = get_settings()


# =============================================================================
# FastAPI-Users Routers
# =============================================================================

# JWT authentication routes: /auth/jwt/login, /auth/jwt/logout
jwt_router = fastapi_users.get_auth_router(auth_backend)

# Registration route: /auth/register
register_router = fastapi_users.get_register_router(UserRead, UserCreate)

# Password reset routes: /auth/forgot-password, /auth/reset-password
reset_password_router = fastapi_users.get_reset_password_router()

# Email verification routes: /auth/request-verify-token, /auth/verify
verify_router = fastapi_users.get_verify_router(UserRead)

# User management routes: /users/me, /users/{id}
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)


# =============================================================================
# Custom Endpoints Router
# =============================================================================

custom_router = APIRouter(tags=["auth"])


@custom_router.get(
    "/me/usage",
    response_model=UsageStatistics,
    summary="Get usage statistics",
    description="Returns current user's translation usage statistics.",
)
async def get_usage_statistics(
    user: Annotated[User, Depends(current_user)],
) -> UsageStatistics:
    """Get current user's usage statistics."""
    # Calculate reset date (start of next month)
    now = datetime.now(timezone.utc)
    if now.month == 12:
        reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    return UsageStatistics(
        minutes_used=user.translation_minutes_used,
        minutes_limit=user.translation_minutes_limit,
        minutes_remaining=user.minutes_remaining,
        tier=user.tier,
        reset_date=reset_date,
    )


@custom_router.post(
    "/me/tier/upgrade",
    response_model=TierUpgradeResponse,
    summary="Upgrade subscription tier",
    description="Placeholder endpoint for tier upgrade. Returns 501 Not Implemented.",
)
async def upgrade_tier(
    request: TierUpgradeRequest,
    user: Annotated[User, Depends(current_verified_user)],
) -> TierUpgradeResponse:
    """Upgrade user's subscription tier.

    This is a placeholder endpoint. Actual implementation will integrate with Stripe.
    """
    logger.info(
        "tier_upgrade_requested",
        user_id=str(user.id),
        current_tier=user.tier,
        target_tier=request.target_tier,
    )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "message": "Tier upgrade is not yet implemented",
            "current_tier": user.tier,
            "target_tier": request.target_tier,
        },
    )


@custom_router.get(
    "/health",
    response_model=AuthHealthResponse,
    summary="Auth system health check",
    description="Checks authentication system health including database connectivity.",
)
async def auth_health_check(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthHealthResponse:
    """Check authentication system health."""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        return AuthHealthResponse(
            status="healthy",
            database="connected",
        )
    except Exception as e:
        logger.error(
            "auth_health_check_failed",
            error=str(e),
        )
        return AuthHealthResponse(
            status="unhealthy",
            database="disconnected",
        )


# =============================================================================
# Main Auth Router Aggregation
# =============================================================================


def get_auth_router() -> APIRouter:
    """Create and configure the main auth router.

    Routes:
    - POST /auth/jwt/login - Login and get JWT
    - POST /auth/jwt/logout - Logout (client-side for JWT)
    - POST /auth/register - User registration
    - POST /auth/forgot-password - Request password reset
    - POST /auth/reset-password - Execute password reset
    - POST /auth/request-verify-token - Request email verification
    - POST /auth/verify - Verify email with token
    - GET /auth/me/usage - Get usage statistics
    - POST /auth/me/tier/upgrade - Upgrade tier (placeholder)
    - GET /auth/health - Auth system health check
    """
    router = APIRouter()

    # Mount FastAPI-Users routers
    router.include_router(jwt_router, prefix="/jwt", tags=["auth"])
    router.include_router(register_router, tags=["auth"])
    router.include_router(reset_password_router, tags=["auth"])
    router.include_router(verify_router, tags=["auth"])

    # Mount custom endpoints
    router.include_router(custom_router)

    return router


def get_users_router() -> APIRouter:
    """Get the users management router.

    Routes:
    - GET /users/me - Get current user
    - PATCH /users/me - Update current user
    - GET /users/{id} - Get user by ID (superuser only)
    - PATCH /users/{id} - Update user (superuser only)
    - DELETE /users/{id} - Delete user (superuser only)
    """
    return users_router
