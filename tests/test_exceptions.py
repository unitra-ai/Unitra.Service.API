"""Tests for custom exception classes."""

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

# =============================================================================
# Base Exception Tests
# =============================================================================


class TestAppException:
    """Tests for base AppException."""

    def test_default_values(self) -> None:
        """Test default exception values."""
        exc = AppException(message="Test error")

        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.details == {}
        assert str(exc) == "Test error"

    def test_custom_values(self) -> None:
        """Test custom exception values."""
        exc = AppException(
            message="Custom error",
            status_code=400,
            error_code="CUSTOM_ERROR",
            details={"field": "value"},
        )

        assert exc.message == "Custom error"
        assert exc.status_code == 400
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == {"field": "value"}


# =============================================================================
# Authentication Error Tests (401)
# =============================================================================


class TestAuthenticationErrors:
    """Tests for authentication errors."""

    def test_authentication_error_defaults(self) -> None:
        """Test AuthenticationError default values."""
        exc = AuthenticationError()

        assert exc.message == "Authentication failed"
        assert exc.status_code == 401
        assert exc.error_code == "AUTH_FAILED"

    def test_authentication_error_custom_message(self) -> None:
        """Test AuthenticationError with custom message."""
        exc = AuthenticationError(message="Token invalid", details={"reason": "expired"})

        assert exc.message == "Token invalid"
        assert exc.details == {"reason": "expired"}

    def test_invalid_credentials_error(self) -> None:
        """Test InvalidCredentialsError."""
        exc = InvalidCredentialsError()

        assert exc.message == "Invalid email or password"
        assert exc.status_code == 401
        assert exc.error_code == "INVALID_CREDENTIALS"

    def test_token_expired_error(self) -> None:
        """Test TokenExpiredError."""
        exc = TokenExpiredError()

        assert exc.message == "Token has expired"
        assert exc.status_code == 401
        assert exc.error_code == "TOKEN_EXPIRED"

    def test_token_invalid_error(self) -> None:
        """Test TokenInvalidError."""
        exc = TokenInvalidError()

        assert exc.message == "Invalid token"
        assert exc.error_code == "TOKEN_INVALID"

    def test_token_invalid_error_custom_reason(self) -> None:
        """Test TokenInvalidError with custom reason."""
        exc = TokenInvalidError(reason="Malformed JWT")

        assert exc.message == "Malformed JWT"

    def test_token_revoked_error(self) -> None:
        """Test TokenRevokedError."""
        exc = TokenRevokedError()

        assert exc.message == "Token has been revoked"
        assert exc.error_code == "TOKEN_REVOKED"


# =============================================================================
# Authorization Error Tests (403)
# =============================================================================


class TestAuthorizationErrors:
    """Tests for authorization errors."""

    def test_authorization_error_defaults(self) -> None:
        """Test AuthorizationError default values."""
        exc = AuthorizationError()

        assert exc.message == "Access denied"
        assert exc.status_code == 403
        assert exc.error_code == "ACCESS_DENIED"

    def test_insufficient_tier_error(self) -> None:
        """Test InsufficientTierError."""
        exc = InsufficientTierError(required_tier="PRO")

        assert "PRO" in exc.message
        assert exc.status_code == 403
        assert exc.error_code == "INSUFFICIENT_TIER"
        assert exc.details == {"required_tier": "PRO"}

    def test_account_inactive_error(self) -> None:
        """Test AccountInactiveError."""
        exc = AccountInactiveError()

        assert exc.message == "Account is inactive"
        assert exc.error_code == "ACCOUNT_INACTIVE"

    def test_email_not_verified_error(self) -> None:
        """Test EmailNotVerifiedError."""
        exc = EmailNotVerifiedError()

        assert exc.message == "Email address not verified"
        assert exc.error_code == "EMAIL_NOT_VERIFIED"


# =============================================================================
# Resource Error Tests (404, 409)
# =============================================================================


class TestResourceErrors:
    """Tests for resource errors."""

    def test_not_found_error_defaults(self) -> None:
        """Test NotFoundError default values."""
        exc = NotFoundError()

        assert exc.message == "Resource not found"
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.details == {"resource": "Resource"}

    def test_not_found_error_with_resource(self) -> None:
        """Test NotFoundError with resource name."""
        exc = NotFoundError(resource="User", identifier="123")

        assert exc.message == "User not found"
        assert exc.details == {"resource": "User", "identifier": "123"}

    def test_resource_conflict_error(self) -> None:
        """Test ResourceConflictError."""
        exc = ResourceConflictError(message="Duplicate entry", details={"field": "email"})

        assert exc.message == "Duplicate entry"
        assert exc.status_code == 409
        assert exc.error_code == "RESOURCE_CONFLICT"

    def test_duplicate_email_error(self) -> None:
        """Test DuplicateEmailError."""
        exc = DuplicateEmailError(email="test@example.com")

        assert exc.message == "Email already registered"
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_EMAIL"
        assert exc.details == {"email": "test@example.com"}


# =============================================================================
# Validation Error Tests (422)
# =============================================================================


class TestValidationErrors:
    """Tests for validation errors."""

    def test_validation_error_defaults(self) -> None:
        """Test ValidationError default values."""
        exc = ValidationError()

        assert exc.message == "Validation error"
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"

    def test_validation_error_with_field(self) -> None:
        """Test ValidationError with field."""
        exc = ValidationError(message="Invalid email format", field="email")

        assert exc.message == "Invalid email format"
        assert exc.details == {"field": "email"}

    def test_validation_error_with_details(self) -> None:
        """Test ValidationError with custom details."""
        exc = ValidationError(
            message="Multiple errors",
            details={"errors": ["error1", "error2"]},
        )

        assert exc.details == {"errors": ["error1", "error2"]}

    def test_invalid_language_error(self) -> None:
        """Test InvalidLanguageError."""
        exc = InvalidLanguageError(lang="xyz")

        assert "xyz" in exc.message
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_LANGUAGE"
        assert exc.details == {"language": "xyz"}


# =============================================================================
# Rate Limiting Error Tests (429)
# =============================================================================


class TestRateLimitingErrors:
    """Tests for rate limiting errors."""

    def test_rate_limit_error_defaults(self) -> None:
        """Test RateLimitError default values."""
        exc = RateLimitError()

        assert exc.message == "Rate limit exceeded"
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.retry_after == 60
        assert exc.details["retry_after"] == 60

    def test_rate_limit_error_custom_retry(self) -> None:
        """Test RateLimitError with custom retry_after."""
        exc = RateLimitError(retry_after=120, details={"endpoint": "/api/translate"})

        assert exc.retry_after == 120
        assert exc.details["retry_after"] == 120
        assert exc.details["endpoint"] == "/api/translate"

    def test_usage_limit_exceeded_error(self) -> None:
        """Test UsageLimitExceededError."""
        exc = UsageLimitExceededError(limit=1000, used=1500)

        assert exc.message == "Weekly usage limit exceeded"
        assert exc.status_code == 429
        assert exc.error_code == "USAGE_LIMIT_EXCEEDED"
        assert exc.details == {"limit": 1000, "used": 1500}


# =============================================================================
# External Service Error Tests (502)
# =============================================================================


class TestExternalServiceErrors:
    """Tests for external service errors."""

    def test_external_service_error(self) -> None:
        """Test ExternalServiceError."""
        exc = ExternalServiceError(service="TestService", message="Connection failed")

        assert "TestService" in exc.message
        assert "Connection failed" in exc.message
        assert exc.status_code == 502
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exc.details == {"service": "TestService"}

    def test_ml_service_error_defaults(self) -> None:
        """Test MLServiceError default values."""
        exc = MLServiceError()

        assert "Translation service unavailable" in exc.message
        assert exc.status_code == 502
        assert exc.error_code == "ML_SERVICE_ERROR"

    def test_ml_service_error_custom_message(self) -> None:
        """Test MLServiceError with custom message."""
        exc = MLServiceError(message="GPU timeout")

        assert "GPU timeout" in exc.message

    def test_stripe_service_error_defaults(self) -> None:
        """Test StripeServiceError default values."""
        exc = StripeServiceError()

        assert "Payment service unavailable" in exc.message
        assert exc.error_code == "STRIPE_SERVICE_ERROR"

    def test_stripe_service_error_custom_message(self) -> None:
        """Test StripeServiceError with custom message."""
        exc = StripeServiceError(message="Card declined")

        assert "Card declined" in exc.message


# =============================================================================
# Exception Inheritance Tests
# =============================================================================


class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy."""

    def test_authentication_errors_inherit_from_app_exception(self) -> None:
        """Test authentication errors inherit from AppException."""
        assert issubclass(AuthenticationError, AppException)
        assert issubclass(InvalidCredentialsError, AuthenticationError)
        assert issubclass(TokenExpiredError, AuthenticationError)
        assert issubclass(TokenInvalidError, AuthenticationError)
        assert issubclass(TokenRevokedError, AuthenticationError)

    def test_authorization_errors_inherit_from_app_exception(self) -> None:
        """Test authorization errors inherit from AppException."""
        assert issubclass(AuthorizationError, AppException)
        assert issubclass(InsufficientTierError, AuthorizationError)
        assert issubclass(AccountInactiveError, AuthorizationError)
        assert issubclass(EmailNotVerifiedError, AuthorizationError)

    def test_resource_errors_inherit_from_app_exception(self) -> None:
        """Test resource errors inherit from AppException."""
        assert issubclass(NotFoundError, AppException)
        assert issubclass(ResourceConflictError, AppException)
        assert issubclass(DuplicateEmailError, ResourceConflictError)

    def test_validation_errors_inherit_from_app_exception(self) -> None:
        """Test validation errors inherit from AppException."""
        assert issubclass(ValidationError, AppException)
        assert issubclass(InvalidLanguageError, ValidationError)

    def test_rate_limit_errors_inherit_from_app_exception(self) -> None:
        """Test rate limit errors inherit from AppException."""
        assert issubclass(RateLimitError, AppException)
        assert issubclass(UsageLimitExceededError, AppException)

    def test_external_service_errors_inherit_from_app_exception(self) -> None:
        """Test external service errors inherit from AppException."""
        assert issubclass(ExternalServiceError, AppException)
        assert issubclass(MLServiceError, ExternalServiceError)
        assert issubclass(StripeServiceError, ExternalServiceError)

    def test_all_exceptions_are_catchable_as_exception(self) -> None:
        """Test all custom exceptions can be caught as Exception."""
        exceptions = [
            AuthenticationError(),
            InvalidCredentialsError(),
            AuthorizationError(),
            NotFoundError(),
            ValidationError(),
            RateLimitError(),
            ExternalServiceError(service="Test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, Exception)
            assert isinstance(exc, AppException)
