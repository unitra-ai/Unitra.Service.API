"""Subscription model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionStatus(str, Enum):
    """Subscription status options."""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"


class SubscriptionPlan(str, Enum):
    """Available subscription plans."""

    BASIC_MONTHLY = "basic_monthly"
    BASIC_YEARLY = "basic_yearly"
    PRO_MONTHLY = "pro_monthly"
    PRO_YEARLY = "pro_yearly"


class Subscription(Base, TimestampMixin):
    """Subscription model for tracking user subscriptions."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        String(50),
        nullable=False,
    )
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="subscriptions",
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan}, status={self.status})>"
