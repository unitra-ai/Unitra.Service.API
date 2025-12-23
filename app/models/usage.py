"""Usage log model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProcessingLocation(str, Enum):
    """Processing location options."""

    LOCAL = "local"
    CLOUD = "cloud"


class UsageLog(Base):
    """Usage log model for tracking translation usage."""

    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    source_lang: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    target_lang: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    processing_location: Mapped[ProcessingLocation] = mapped_column(
        String(20),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_usage_logs_user_created", "user_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<UsageLog(id={self.id}, user_id={self.user_id}, tokens={self.tokens_used})>"
