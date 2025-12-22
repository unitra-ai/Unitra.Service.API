"""User model for FastAPI-Users authentication."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken
    from app.models.subscription import Subscription


class UserTier(str, Enum):
    """User subscription tier levels."""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Tier limits configuration
TIER_LIMITS = {
    UserTier.FREE: {"minutes": 60, "price": 0},
    UserTier.BASIC: {"minutes": 300, "price": 9.99},
    UserTier.PRO: {"minutes": 1200, "price": 29.99},
    UserTier.ENTERPRISE: {"minutes": -1, "price": -1},  # Unlimited, custom pricing
}


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model for authentication and authorization.

    Inherits from SQLAlchemyBaseUserTableUUID which provides:
    - id: UUID primary key
    - email: str (unique, indexed)
    - hashed_password: str
    - is_active: bool (default True)
    - is_superuser: bool (default False)
    - is_verified: bool (default False)
    """

    __tablename__ = "users"

    # Subscription tier
    tier: Mapped[str] = mapped_column(
        String(50),
        default=UserTier.FREE.value,
        nullable=False,
    )

    # Stripe integration
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    # Usage tracking (monthly)
    translation_minutes_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    translation_minutes_limit: Mapped[int] = mapped_column(
        Integer,
        default=60,  # FREE tier default
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    login_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def tier_enum(self) -> UserTier:
        """Get tier as enum."""
        return UserTier(self.tier)

    @property
    def minutes_remaining(self) -> int:
        """Calculate remaining translation minutes for current month."""
        if self.translation_minutes_limit == -1:  # Unlimited
            return -1
        return max(0, self.translation_minutes_limit - self.translation_minutes_used)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tier={self.tier})>"
