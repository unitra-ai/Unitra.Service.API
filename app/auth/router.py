"""Authentication routers for FastAPI-Users."""

from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
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
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TierUpgradeRequest,
    TierUpgradeResponse,
    UsageStatistics,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.config import get_settings
from app.db.redis import RedisClient, get_redis
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


@custom_router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout and invalidate token",
    description="Logout user and blacklist the current JWT token server-side.",
)
async def logout(
    request: Request,
    user: Annotated[User, Depends(current_user)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    authorization: str = Header(...),
) -> LogoutResponse:
    """Logout user and blacklist the JWT token.

    This endpoint extracts the JTI from the token and adds it to the Redis
    blacklist, ensuring the token cannot be reused even before expiration.
    """
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )

        token = authorization.replace("Bearer ", "")

        # Decode token to get JTI and expiration
        # Note: FastAPI-Users tokens use "unitra:auth" as audience
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience="unitra:auth",
        )

        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti:
            # Token doesn't have JTI, still log out successfully
            logger.warning(
                "logout_no_jti",
                user_id=str(user.id),
                message="Token without JTI, cannot blacklist",
            )
            return LogoutResponse(
                success=True,
                message="Logged out (token will remain valid until expiration)",
            )

        # Calculate remaining TTL for the token
        now = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - now) if exp else settings.jwt_lifetime_seconds

        if ttl > 0:
            # Blacklist the token
            await redis.blacklist_token(jti, ttl)

        logger.info(
            "user_logged_out",
            user_id=str(user.id),
            jti=jti,
            token_blacklisted=True,
        )

        # Also clear Redis session cache
        await redis.delete_session(str(user.id))

        return LogoutResponse(
            success=True,
            message="Logged out successfully. Token has been invalidated.",
        )

    except JWTError as e:
        logger.error(
            "logout_token_decode_error",
            user_id=str(user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@custom_router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Get a new access token using a refresh token.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    redis: Annotated[RedisClient, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RefreshTokenResponse:
    """Refresh access token using a refresh token.

    This endpoint validates the refresh token and issues a new access token.
    The old access token (if blacklisted) remains blacklisted.
    """
    from app.auth.backend import get_user_db, CustomJWTStrategy
    from app.auth.models import User

    try:
        # Decode refresh token
        payload = jwt.decode(
            request.refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        # Verify it's a refresh token type
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Expected refresh token.",
            )

        # Check if refresh token is blacklisted
        jti = payload.get("jti")
        if jti and await redis.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no user ID",
            )

        from sqlalchemy import select

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        # Generate new access token using custom strategy
        strategy = CustomJWTStrategy(
            secret=settings.secret_key,
            lifetime_seconds=settings.jwt_lifetime_seconds,
            token_audience=["unitra:auth"],
            algorithm=settings.algorithm,
        )
        new_access_token = await strategy.write_token(user)

        logger.info(
            "token_refreshed",
            user_id=str(user.id),
        )

        return RefreshTokenResponse(
            access_token=new_access_token,
            token_type="bearer",
        )

    except JWTError as e:
        logger.error(
            "refresh_token_error",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
        )


# =============================================================================
# Main Auth Router Aggregation
# =============================================================================


def get_auth_router() -> APIRouter:
    """Create and configure the main auth router.

    Routes:
    - POST /auth/jwt/login - Login and get JWT
    - POST /auth/jwt/logout - Logout (client-side for JWT, FastAPI-Users default)
    - POST /auth/logout - Logout with server-side token blacklisting
    - POST /auth/refresh - Refresh access token using refresh token
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
