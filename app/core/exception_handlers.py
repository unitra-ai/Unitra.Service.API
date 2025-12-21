"""Exception handlers for FastAPI application."""

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException, RateLimitError

logger = structlog.get_logger("app.exception_handlers")


def create_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a consistent error response structure."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Handle custom AppException and subclasses."""
    logger.warning(
        "app_exception",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        method=request.method,
    )

    response = JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
    )

    # Add Retry-After header for rate limit errors
    if isinstance(exc, RateLimitError):
        response.headers["Retry-After"] = str(exc.retry_after)

    return response


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field information."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        "validation_error",
        path=request.url.path,
        method=request.method,
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        ),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
