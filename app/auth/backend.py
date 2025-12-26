"""JWT Authentication backend for FastAPI-Users."""

import uuid
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.jwt import generate_jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.manager import UserManager
from app.auth.models import User
from app.config import get_settings
from app.db.session import get_db_session

settings = get_settings()


# =============================================================================
# Database Adapter
# =============================================================================


async def get_user_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, UUID], None]:
    """Get SQLAlchemy user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


# =============================================================================
# User Manager Factory
# =============================================================================


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, UUID] = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    """Get user manager instance."""
    yield UserManager(user_db)


# =============================================================================
# JWT Authentication Backend
# =============================================================================


class CustomJWTStrategy(JWTStrategy[User, UUID]):
    """Custom JWT strategy with additional claims including JTI for token revocation."""

    async def write_token(self, user: User) -> str:
        """Create JWT token with custom claims including JTI for blacklisting."""
        # Generate unique token ID for blacklisting support
        jti = str(uuid.uuid4())

        # Add custom claims to the token
        data = {
            "sub": str(user.id),
            "aud": self.token_audience,
            "jti": jti,  # JWT ID for token revocation
            # Custom claims
            "tier": user.tier,
            "minutes_remaining": user.minutes_remaining,
        }
        return generate_jwt(data, self.encode_key, self.lifetime_seconds, algorithm=self.algorithm)


def get_jwt_strategy() -> CustomJWTStrategy:
    """Get JWT strategy instance."""
    return CustomJWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.jwt_lifetime_seconds,
        token_audience=["unitra:auth"],
        algorithm=settings.algorithm,
    )


# Bearer token transport
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Authentication backend combining transport and strategy
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# =============================================================================
# FastAPI-Users Instance
# =============================================================================

fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)


# =============================================================================
# Dependency Shortcuts
# =============================================================================

# Active user required (is_active=True)
current_user = fastapi_users.current_user(active=True)

# Active and verified user required
current_verified_user = fastapi_users.current_user(active=True, verified=True)

# Superuser required
current_superuser = fastapi_users.current_user(active=True, superuser=True)

# Optional user (returns None if not authenticated)
optional_current_user = fastapi_users.current_user(active=True, optional=True)
