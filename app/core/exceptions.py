"""Custom exception classes."""

from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


# =============================================================================
# Authentication Errors (401)
# =============================================================================


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTH_FAILED",
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""

    def __init__(self) -> None:
        super().__init__(message="Invalid email or password")
        self.error_code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self) -> None:
        super().__init__(message="Token has expired")
        self.error_code = "TOKEN_EXPIRED"


class TokenInvalidError(AuthenticationError):
    """Invalid token."""

    def __init__(self, reason: str = "Invalid token") -> None:
        super().__init__(message=reason)
        self.error_code = "TOKEN_INVALID"


class TokenRevokedError(AuthenticationError):
    """Token has been revoked."""

    def __init__(self) -> None:
        super().__init__(message="Token has been revoked")
        self.error_code = "TOKEN_REVOKED"


# =============================================================================
# Authorization Errors (403)
# =============================================================================


class AuthorizationError(AppException):
    """User not authorized for this action."""

    def __init__(
        self,
        message: str = "Access denied",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="ACCESS_DENIED",
            details=details,
        )


class InsufficientTierError(AuthorizationError):
    """User's tier is insufficient for this feature."""

    def __init__(self, required_tier: str) -> None:
        super().__init__(
            message=f"This feature requires {required_tier} tier or higher",
            details={"required_tier": required_tier},
        )
        self.error_code = "INSUFFICIENT_TIER"


class AccountInactiveError(AuthorizationError):
    """User account is inactive."""

    def __init__(self) -> None:
        super().__init__(message="Account is inactive")
        self.error_code = "ACCOUNT_INACTIVE"


class EmailNotVerifiedError(AuthorizationError):
    """User email is not verified."""

    def __init__(self) -> None:
        super().__init__(message="Email address not verified")
        self.error_code = "EMAIL_NOT_VERIFIED"


# =============================================================================
# Resource Errors (404, 409)
# =============================================================================


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str | None = None,
    ) -> None:
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=details,
        )


class ResourceConflictError(AppException):
    """Resource conflict (e.g., duplicate email)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="RESOURCE_CONFLICT",
            details=details,
        )


class DuplicateEmailError(ResourceConflictError):
    """Email already exists."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message="Email already registered",
            details={"email": email},
        )
        self.error_code = "DUPLICATE_EMAIL"


# =============================================================================
# Validation Errors (422)
# =============================================================================


class ValidationError(AppException):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation error",
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if field and not details:
            details = {"field": field}
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details or {},
        )


class InvalidLanguageError(ValidationError):
    """Invalid language code."""

    def __init__(self, lang: str) -> None:
        super().__init__(
            message=f"Invalid language code: {lang}",
            details={"language": lang},
        )
        self.error_code = "INVALID_LANGUAGE"


# =============================================================================
# Rate Limiting / Usage Errors (429)
# =============================================================================


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        retry_after: int = 60,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after, **(details or {})},
        )
        self.retry_after = retry_after


class UsageLimitExceededError(AppException):
    """Weekly usage limit exceeded."""

    def __init__(self, limit: int, used: int) -> None:
        super().__init__(
            message="Weekly usage limit exceeded",
            status_code=429,
            error_code="USAGE_LIMIT_EXCEEDED",
            details={"limit": limit, "used": used},
        )


# =============================================================================
# External Service Errors (502)
# =============================================================================


class ExternalServiceError(AppException):
    """External service error (ML service, Stripe, etc.)."""

    def __init__(
        self,
        service: str,
        message: str = "Service unavailable",
    ) -> None:
        super().__init__(
            message=f"{service}: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )


class MLServiceError(ExternalServiceError):
    """ML translation service error."""

    def __init__(self, message: str = "Translation service unavailable") -> None:
        super().__init__(service="ML Service", message=message)
        self.error_code = "ML_SERVICE_ERROR"


class StripeServiceError(ExternalServiceError):
    """Stripe payment service error."""

    def __init__(self, message: str = "Payment service unavailable") -> None:
        super().__init__(service="Stripe", message=message)
        self.error_code = "STRIPE_SERVICE_ERROR"
