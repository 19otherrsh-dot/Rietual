"""
Goal-conflict detection models.

Reference: Habit Engine §8.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from src.core.types import UUID  # portable: native uuid on Postgres, CHAR(32) elsewhere
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ConflictAlert(Base):
    """
    A detected scheduling conflict needing user resolution.
    Surfaced *before* the day, never after the miss.
    """
    __tablename__ = "conflict_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The primary occurrence causing the conflict. (Nullable if representing a cluster without a single head)
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("occurrences.id", ondelete="CASCADE"), nullable=True, index=True
    )

    conflict_type: Mapped[str] = mapped_column(
        Enum("hard_calendar", "hard_overlap", "soft_density", name="conflict_type_enum"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(512), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("pending", "resolved_move", "resolved_rest", "resolved_ignore", name="conflict_status_enum"),
        default="pending",
        nullable=False,
    )

    # The day the conflict was detected for
    detected_for_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
