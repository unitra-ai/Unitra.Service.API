"""Tests for Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    BaseResponse,
    ErrorDetail,
    ErrorResponse,
    IDMixin,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
    TimestampMixin,
)


# =============================================================================
# Error Schema Tests
# =============================================================================


class TestErrorDetail:
    """Tests for ErrorDetail schema."""

    def test_create_with_required_fields(self) -> None:
        """Test creating ErrorDetail with required fields."""
        error = ErrorDetail(code="TEST_ERROR", message="Test message")

        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details == {}

    def test_create_with_details(self) -> None:
        """Test creating ErrorDetail with details."""
        error = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details={"field": "email", "reason": "invalid"},
        )

        assert error.details == {"field": "email", "reason": "invalid"}

    def test_serialization(self) -> None:
        """Test ErrorDetail serialization."""
        error = ErrorDetail(code="ERROR", message="Message", details={"key": "value"})

        data = error.model_dump()

        assert data == {
            "code": "ERROR",
            "message": "Message",
            "details": {"key": "value"},
        }


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_create_error_response(self) -> None:
        """Test creating ErrorResponse."""
        response = ErrorResponse(
            error=ErrorDetail(code="ERROR", message="Something went wrong")
        )

        assert response.error.code == "ERROR"
        assert response.error.message == "Something went wrong"

    def test_serialization(self) -> None:
        """Test ErrorResponse serialization."""
        response = ErrorResponse(
            error=ErrorDetail(code="NOT_FOUND", message="Resource not found")
        )

        data = response.model_dump()

        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


# =============================================================================
# Success Schema Tests
# =============================================================================


class TestSuccessResponse:
    """Tests for SuccessResponse schema."""

    def test_create_with_data(self) -> None:
        """Test creating SuccessResponse with data."""
        response = SuccessResponse[dict](data={"id": 1, "name": "Test"})

        assert response.data == {"id": 1, "name": "Test"}
        assert response.meta is None

    def test_create_with_meta(self) -> None:
        """Test creating SuccessResponse with metadata."""
        response = SuccessResponse[str](
            data="success",
            meta={"processing_time": 0.5},
        )

        assert response.data == "success"
        assert response.meta == {"processing_time": 0.5}

    def test_generic_type_list(self) -> None:
        """Test SuccessResponse with list data."""
        response = SuccessResponse[list[int]](data=[1, 2, 3])

        assert response.data == [1, 2, 3]

    def test_serialization(self) -> None:
        """Test SuccessResponse serialization."""
        response = SuccessResponse[dict](
            data={"key": "value"},
            meta={"extra": "info"},
        )

        data = response.model_dump()

        assert data["data"] == {"key": "value"}
        assert data["meta"] == {"extra": "info"}


class TestMessageResponse:
    """Tests for MessageResponse schema."""

    def test_create_message_response(self) -> None:
        """Test creating MessageResponse."""
        response = MessageResponse(message="Operation successful")

        assert response.message == "Operation successful"

    def test_serialization(self) -> None:
        """Test MessageResponse serialization."""
        response = MessageResponse(message="Done")

        data = response.model_dump()

        assert data == {"message": "Done"}


# =============================================================================
# Pagination Schema Tests
# =============================================================================


class TestPaginationMeta:
    """Tests for PaginationMeta schema."""

    def test_create_pagination_meta(self) -> None:
        """Test creating PaginationMeta."""
        meta = PaginationMeta(
            total=100,
            page=1,
            per_page=10,
            total_pages=10,
        )

        assert meta.total == 100
        assert meta.page == 1
        assert meta.per_page == 10
        assert meta.total_pages == 10

    def test_create_from_counts(self) -> None:
        """Test creating PaginationMeta from counts."""
        meta = PaginationMeta.create(total=95, page=2, per_page=10)

        assert meta.total == 95
        assert meta.page == 2
        assert meta.per_page == 10
        assert meta.total_pages == 10  # ceil(95/10) = 10

    def test_create_with_exact_division(self) -> None:
        """Test pagination with exact division."""
        meta = PaginationMeta.create(total=100, page=1, per_page=10)

        assert meta.total_pages == 10

    def test_create_with_single_item(self) -> None:
        """Test pagination with single item."""
        meta = PaginationMeta.create(total=1, page=1, per_page=10)

        assert meta.total_pages == 1

    def test_create_with_zero_items(self) -> None:
        """Test pagination with zero items."""
        meta = PaginationMeta.create(total=0, page=1, per_page=10)

        assert meta.total_pages == 0

    def test_create_with_zero_per_page(self) -> None:
        """Test pagination with zero per_page (edge case)."""
        meta = PaginationMeta.create(total=100, page=1, per_page=0)

        assert meta.total_pages == 0

    def test_serialization(self) -> None:
        """Test PaginationMeta serialization."""
        meta = PaginationMeta.create(total=50, page=3, per_page=10)

        data = meta.model_dump()

        assert data == {
            "total": 50,
            "page": 3,
            "per_page": 10,
            "total_pages": 5,
        }


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_create_paginated_response(self) -> None:
        """Test creating PaginatedResponse."""
        response = PaginatedResponse[dict](
            data=[{"id": 1}, {"id": 2}],
            meta=PaginationMeta(total=100, page=1, per_page=10, total_pages=10),
        )

        assert len(response.data) == 2
        assert response.meta.total == 100

    def test_empty_data(self) -> None:
        """Test PaginatedResponse with empty data."""
        response = PaginatedResponse[dict](
            data=[],
            meta=PaginationMeta(total=0, page=1, per_page=10, total_pages=0),
        )

        assert response.data == []
        assert response.meta.total == 0

    def test_serialization(self) -> None:
        """Test PaginatedResponse serialization."""
        response = PaginatedResponse[str](
            data=["a", "b", "c"],
            meta=PaginationMeta.create(total=3, page=1, per_page=10),
        )

        data = response.model_dump()

        assert data["data"] == ["a", "b", "c"]
        assert "meta" in data
        assert data["meta"]["total"] == 3


# =============================================================================
# Mixin Tests
# =============================================================================


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_create_with_timestamps(self) -> None:
        """Test creating model with timestamps."""

        class TestModel(TimestampMixin):
            name: str

        now = datetime.now(timezone.utc)
        model = TestModel(name="test", created_at=now, updated_at=now)

        assert model.created_at == now
        assert model.updated_at == now

    def test_timestamp_serialization(self) -> None:
        """Test timestamp serialization."""

        class TestModel(TimestampMixin):
            name: str

        now = datetime.now(timezone.utc)
        model = TestModel(name="test", created_at=now, updated_at=now)

        data = model.model_dump()

        assert "created_at" in data
        assert "updated_at" in data


class TestIDMixin:
    """Tests for IDMixin."""

    def test_create_with_id(self) -> None:
        """Test creating model with ID."""

        class TestModel(IDMixin):
            name: str

        model = TestModel(id="550e8400-e29b-41d4-a716-446655440000", name="test")

        assert model.id == "550e8400-e29b-41d4-a716-446655440000"

    def test_id_serialization(self) -> None:
        """Test ID serialization."""

        class TestModel(IDMixin):
            name: str

        model = TestModel(id="123", name="test")

        data = model.model_dump()

        assert data["id"] == "123"


# =============================================================================
# BaseResponse Tests
# =============================================================================


class TestBaseResponse:
    """Tests for BaseResponse."""

    def test_from_attributes_config(self) -> None:
        """Test BaseResponse allows from_attributes."""

        class TestResponse(BaseResponse):
            name: str
            value: int

        # Simulate ORM object
        class MockORM:
            name = "test"
            value = 42

        response = TestResponse.model_validate(MockORM())

        assert response.name == "test"
        assert response.value == 42

    def test_populate_by_name_config(self) -> None:
        """Test BaseResponse allows population by field name."""

        class TestResponse(BaseResponse):
            user_name: str

        response = TestResponse(user_name="john")

        assert response.user_name == "john"


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestSchemaValidation:
    """Tests for schema validation."""

    def test_error_detail_requires_code(self) -> None:
        """Test ErrorDetail requires code field."""
        with pytest.raises(ValidationError):
            ErrorDetail(message="Test")  # type: ignore

    def test_error_detail_requires_message(self) -> None:
        """Test ErrorDetail requires message field."""
        with pytest.raises(ValidationError):
            ErrorDetail(code="ERROR")  # type: ignore

    def test_pagination_meta_requires_all_fields(self) -> None:
        """Test PaginationMeta requires all fields."""
        with pytest.raises(ValidationError):
            PaginationMeta(total=100)  # type: ignore

    def test_paginated_response_requires_meta(self) -> None:
        """Test PaginatedResponse requires meta."""
        with pytest.raises(ValidationError):
            PaginatedResponse(data=[1, 2, 3])  # type: ignore


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in schemas."""

    def test_error_detail_with_nested_details(self) -> None:
        """Test ErrorDetail with deeply nested details."""
        error = ErrorDetail(
            code="COMPLEX_ERROR",
            message="Complex error",
            details={
                "level1": {
                    "level2": {
                        "level3": "deep value",
                    }
                }
            },
        )

        assert error.details["level1"]["level2"]["level3"] == "deep value"

    def test_success_response_with_none_data(self) -> None:
        """Test SuccessResponse with None data."""
        response = SuccessResponse[None](data=None)

        assert response.data is None

    def test_large_pagination(self) -> None:
        """Test pagination with large numbers."""
        meta = PaginationMeta.create(
            total=1_000_000_000,
            page=50_000,
            per_page=20,
        )

        assert meta.total_pages == 50_000_000

    def test_unicode_in_error_message(self) -> None:
        """Test ErrorDetail with unicode message."""
        error = ErrorDetail(
            code="ERROR",
            message="错误信息 🚫",
            details={"field": "用户名"},
        )

        assert "错误信息" in error.message
        assert error.details["field"] == "用户名"
