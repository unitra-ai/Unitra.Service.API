"""Common response schemas."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


# =============================================================================
# Error Schemas
# =============================================================================


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail


# =============================================================================
# Success Schemas
# =============================================================================


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response with data."""

    data: T
    meta: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# =============================================================================
# Pagination Schemas
# =============================================================================


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    per_page: int
    total_pages: int

    @classmethod
    def create(cls, total: int, page: int, per_page: int) -> "PaginationMeta":
        """Create pagination meta from counts."""
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with list data."""

    data: list[T]
    meta: PaginationMeta


# =============================================================================
# Mixins
# =============================================================================


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps."""

    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    """Mixin for models with UUID ID."""

    id: str


# =============================================================================
# Base Response Model
# =============================================================================


class BaseResponse(BaseModel):
    """Base response model with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
