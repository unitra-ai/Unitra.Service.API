"""Core module with security, exceptions, middleware, and limits."""

from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from app.core.limits import (
    TIER_LIMITS,
    Tier,
    TierLimits,
    get_tier_limits,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)

__all__ = [
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ExternalServiceError",
    # Security
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "hash_password",
    "verify_password",
    # Limits
    "Tier",
    "TierLimits",
    "TIER_LIMITS",
    "get_tier_limits",
]
