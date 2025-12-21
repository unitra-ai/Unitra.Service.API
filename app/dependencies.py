"""Shared dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import (
    AccountInactiveError,
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.security import verify_token
from app.db.redis import RedisClient, get_redis_client
from app.db.session import get_db_session

# =============================================================================
# Settings Dependency
# =============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]

# =============================================================================
# Database Session Dependency
# =============================================================================

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# =============================================================================
# Redis Client Dependency
# =============================================================================

RedisDep = Annotated[RedisClient, Depends(get_redis_client)]


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate user ID from Authorization header.

    Returns the user ID (sub claim) from a valid JWT token.
    Does NOT fetch the user from database - use get_current_user for that.
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid authorization header format")

    token = authorization.split(" ", 1)[1]

    try:
        payload = verify_token(token, token_type="access")
    except AuthenticationError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError() from e
        raise TokenInvalidError(str(e)) from e

    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidError("Token missing subject claim")

    return user_id


CurrentUserId = Annotated[str, Depends(get_current_user_id)]


async def get_optional_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract user ID from Authorization header, or None if not present.

    Useful for endpoints that work with or without authentication.
    """
    if not authorization:
        return None

    try:
        return await get_current_user_id(authorization)
    except AuthenticationError:
        return None


OptionalUserId = Annotated[str | None, Depends(get_optional_user_id)]


# =============================================================================
# Full User Dependencies (requires database lookup)
# =============================================================================

# Note: These will be implemented when user service is created.
# For now, we provide the user_id-based dependencies above.

# Example implementation (to be added later):
#
# async def get_current_user(
#     user_id: CurrentUserId,
#     db: DbSessionDep,
# ) -> User:
#     """Get current authenticated user from database."""
#     from app.services.user import get_user_by_id
#
#     user = await get_user_by_id(db, user_id)
#     if not user:
#         raise AuthenticationError("User not found")
#     if not user.is_active:
#         raise AccountInactiveError()
#
#     return user
#
# CurrentUser = Annotated[User, Depends(get_current_user)]
