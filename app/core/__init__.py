"""Core module with security, exceptions, middleware, and limits."""

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import (
    AccountInactiveError,
    AppException,
    AuthenticationError,
    AuthorizationError,
    DuplicateEmailError,
    EmailNotVerifiedError,
    ExternalServiceError,
    InsufficientTierError,
    InvalidCredentialsError,
    InvalidLanguageError,
    MLServiceError,
    NotFoundError,
    RateLimitError,
    ResourceConflictError,
    StripeServiceError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    UsageLimitExceededError,
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
    # Base Exception
    "AppException",
    # Authentication Errors
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenRevokedError",
    # Authorization Errors
    "AuthorizationError",
    "InsufficientTierError",
    "AccountInactiveError",
    "EmailNotVerifiedError",
    # Resource Errors
    "NotFoundError",
    "ResourceConflictError",
    "DuplicateEmailError",
    # Validation Errors
    "ValidationError",
    "InvalidLanguageError",
    # Rate Limiting / Usage Errors
    "RateLimitError",
    "UsageLimitExceededError",
    # External Service Errors
    "ExternalServiceError",
    "MLServiceError",
    "StripeServiceError",
    # Exception Handlers
    "register_exception_handlers",
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
