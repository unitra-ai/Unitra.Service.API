"""Tests for exception handlers."""

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.core.exception_handlers import (
    app_exception_handler,
    create_error_response,
    generic_exception_handler,
    register_exception_handlers,
    validation_exception_handler,
)
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)


# =============================================================================
# Error Response Tests
# =============================================================================


class TestCreateErrorResponse:
    """Tests for create_error_response function."""

    def test_basic_error_response(self) -> None:
        """Test basic error response creation."""
        response = create_error_response(
            code="TEST_ERROR",
            message="Test error message",
        )

        assert response == {
            "error": {
                "code": "TEST_ERROR",
                "message": "Test error message",
                "details": {},
            }
        }

    def test_error_response_with_details(self) -> None:
        """Test error response with details."""
        response = create_error_response(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details={"field": "email", "reason": "invalid format"},
        )

        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["message"] == "Validation failed"
        assert response["error"]["details"] == {"field": "email", "reason": "invalid format"}

    def test_error_response_with_none_details(self) -> None:
        """Test error response with None details defaults to empty dict."""
        response = create_error_response(
            code="ERROR",
            message="Message",
            details=None,
        )

        assert response["error"]["details"] == {}


# =============================================================================
# App Exception Handler Tests
# =============================================================================


class TestAppExceptionHandler:
    """Tests for app_exception_handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create a mock request."""
        from unittest.mock import MagicMock

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        return request

    @pytest.mark.asyncio
    async def test_handles_authentication_error(self, mock_request: Request) -> None:
        """Test handling AuthenticationError."""
        exc = AuthenticationError(message="Invalid token")

        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == 401
        body = response.body.decode()
        assert "AUTH_FAILED" in body or "Invalid token" in body

    @pytest.mark.asyncio
    async def test_handles_not_found_error(self, mock_request: Request) -> None:
        """Test handling NotFoundError."""
        exc = NotFoundError(resource="User", identifier="123")

        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error_with_header(self, mock_request: Request) -> None:
        """Test RateLimitError includes Retry-After header."""
        exc = RateLimitError(retry_after=120)

        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "120"

    @pytest.mark.asyncio
    async def test_handles_app_exception_with_details(self, mock_request: Request) -> None:
        """Test handling AppException with details."""
        exc = AppException(
            message="Custom error",
            status_code=400,
            error_code="CUSTOM_ERROR",
            details={"extra": "info"},
        )

        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == 400


# =============================================================================
# Validation Exception Handler Tests
# =============================================================================


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create a mock request."""
        from unittest.mock import MagicMock

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "POST"
        return request

    @pytest.mark.asyncio
    async def test_handles_validation_error(self, mock_request: Request) -> None:
        """Test handling RequestValidationError."""
        # Create a mock validation error
        errors = [
            {
                "loc": ("body", "email"),
                "msg": "value is not a valid email address",
                "type": "value_error.email",
            }
        ]

        class MockValidationError(RequestValidationError):
            def errors(self):
                return errors

        exc = MockValidationError(errors=[])
        exc.errors = lambda: errors  # type: ignore

        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == 422
        body = response.body.decode()
        assert "VALIDATION_ERROR" in body

    @pytest.mark.asyncio
    async def test_formats_field_path_correctly(self, mock_request: Request) -> None:
        """Test field path formatting for nested fields."""
        errors = [
            {
                "loc": ("body", "user", "address", "street"),
                "msg": "field required",
                "type": "value_error.missing",
            }
        ]

        class MockValidationError(RequestValidationError):
            def errors(self):
                return errors

        exc = MockValidationError(errors=[])
        exc.errors = lambda: errors  # type: ignore

        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == 422
        # The field should be formatted as "body.user.address.street"
        body = response.body.decode()
        assert "body.user.address.street" in body


# =============================================================================
# Generic Exception Handler Tests
# =============================================================================


class TestGenericExceptionHandler:
    """Tests for generic_exception_handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create a mock request."""
        from unittest.mock import MagicMock

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        return request

    @pytest.mark.asyncio
    async def test_handles_unexpected_exception(self, mock_request: Request) -> None:
        """Test handling unexpected exceptions."""
        exc = ValueError("Something went wrong")

        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_ERROR" in body
        # Should not expose internal error details
        assert "Something went wrong" not in body

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self, mock_request: Request) -> None:
        """Test handling RuntimeError."""
        exc = RuntimeError("Runtime failure")

        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500


# =============================================================================
# Exception Handler Registration Tests
# =============================================================================


class TestRegisterExceptionHandlers:
    """Tests for register_exception_handlers."""

    def test_registers_handlers(self) -> None:
        """Test that handlers are registered on the app."""
        test_app = FastAPI()

        register_exception_handlers(test_app)

        # Check that exception handlers are registered
        assert AppException in test_app.exception_handlers
        assert RequestValidationError in test_app.exception_handlers
        assert Exception in test_app.exception_handlers


# =============================================================================
# Integration Tests
# =============================================================================


class TestExceptionHandlerIntegration:
    """Integration tests for exception handlers with real app."""

    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_request(
        self, async_client: AsyncClient
    ) -> None:
        """Test validation error is properly formatted."""
        # Send invalid JSON to translate endpoint
        response = await async_client.post(
            "/api/v1/translate",
            json={"invalid": "data"},  # Missing required fields
        )

        # Should get 422 or 501 depending on implementation
        assert response.status_code in [422, 501]

    @pytest.mark.asyncio
    async def test_not_found_for_unknown_endpoint(
        self, async_client: AsyncClient
    ) -> None:
        """Test 404 for unknown endpoints."""
        response = await async_client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_error_response_structure(
        self, async_client: AsyncClient
    ) -> None:
        """Test error responses have consistent structure."""
        response = await async_client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data  # FastAPI default for 404
