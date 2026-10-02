"""
Occurrence ORM model — Habit Engine §4 (scheduling).

Key: scheduled_local is stored as TIMESTAMP WITH TIME ZONE but always
set from the user's local wall clock + IANA timezone. A 07:00 habit
stays at 07:00 through DST transitions and timezone changes (§4.2).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from src.core.types import UUID  # portable: native uuid on Postgres, CHAR(32) elsewhere
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Occurrence(Base):
    __tablename__ = "occurrences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Wall-clock local time + timezone (Habit Engine §4.2)
    scheduled_local: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_timezone: Mapped[str] = mapped_column(String(64), nullable=False)  # IANA tz

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # prompt_policy: probe = deliberately withheld prompt (Habit Engine §5.3)
    prompt_policy: Mapped[str] = mapped_column(
        Enum("prompt", "suppress", "probe", name="prompt_policy_enum"), nullable=False
    )
    prompt_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Delivery, not send, is what attribution turns on (§6.1). Stored rather
    # than only consumed: `unprompted` below is derived from it, and a derived
    # metric whose input was never persisted cannot be audited or recomputed if
    # the rule changes — which for the primary success metric is not a
    # position we want to be in.
    prompt_delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_source: Mapped[str | None] = mapped_column(
        Enum("app", "widget", "watch", "integration", name="completion_source_enum"),
        nullable=True,
    )

    # Computed: completion before prompt delivery time (Habit Engine §6.1)
    # Uses DELIVERY time, not send time (delayed delivery handled correctly)
    unprompted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    outcome: Mapped[str | None] = mapped_column(
        Enum(
            "completed",
            "skipped",
            "missed",
            "rest",          # pre-emptive skip = rest outcome, not a miss (Habit Engine §8)
            name="occurrence_outcome_enum",
        ),
        nullable=True,
    )
    skip_annotation: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
