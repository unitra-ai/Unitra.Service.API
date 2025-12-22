"""Pydantic schemas for user authentication."""

from datetime import datetime
from uuid import UUID

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, Field

from app.auth.models import UserTier


class UserRead(schemas.BaseUser[UUID]):
    """Schema for reading user data."""

    tier: str = Field(default=UserTier.FREE.value)
    stripe_customer_id: str | None = None
    translation_minutes_used: int = 0
    translation_minutes_limit: int = 60
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    login_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user."""

    tier: str = Field(default=UserTier.FREE.value)

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""

    # Users cannot update their tier directly (use upgrade endpoint)
    # They can only update email and password via BaseUserUpdate

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Custom Response Schemas
# =============================================================================


class UsageStatistics(BaseModel):
    """User's translation usage statistics."""

    minutes_used: int = Field(description="Minutes used this month")
    minutes_limit: int = Field(description="Monthly limit (-1 for unlimited)")
    minutes_remaining: int = Field(description="Remaining minutes (-1 for unlimited)")
    tier: str = Field(description="Current subscription tier")
    reset_date: datetime | None = Field(description="When usage resets (start of next month)")

    model_config = ConfigDict(from_attributes=True)


class TierUpgradeRequest(BaseModel):
    """Request to upgrade user tier."""

    target_tier: str = Field(description="Target tier to upgrade to")

    model_config = ConfigDict(from_attributes=True)


class TierUpgradeResponse(BaseModel):
    """Response for tier upgrade request."""

    success: bool
    message: str
    checkout_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthHealthResponse(BaseModel):
    """Authentication system health check response."""

    status: str = Field(description="Health status: healthy or unhealthy")
    database: str = Field(description="Database connection status")

    model_config = ConfigDict(from_attributes=True)
