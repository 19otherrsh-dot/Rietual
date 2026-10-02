"""
Failure Layer ORM models.

Reference: SPEC-failure-layer-v1 §10 (data model).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from src.core.types import JSON_TYPE, UUID  # portable across Postgres and SQLite
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Miss(Base):
    """
    One row per detected miss.  This is the core record for §11.1's headline metric:
    lapse recovery rate = completions within 72h of a miss ÷ total misses.
    """
    __tablename__ = "misses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("occurrences.id"), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Populated from the Occurrence's skip annotation (§1.1)
    skip_annotation: Mapped[str | None] = mapped_column(String(64), nullable=True)

    recovery_break_shown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recovery_break_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Set when the user completes this habit within 72h — the headline metric
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    depth: Mapped[str] = mapped_column(
        Enum("lapsed_1", "lapsed_2", "dormant", name="miss_depth_enum"), nullable=False
    )


class HabitStateLog(Base):
    """
    Audit log of every habit state transition.
    Replaces mutable state on Habit for historical analysis.
    """
    __tablename__ = "habit_state_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    paused_reason: Mapped[str | None] = mapped_column(
        Enum("transition", "user", "illness", "pause_clause", name="pause_reason_enum_fl"),
        nullable=True,
    )
    event: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecoverySelfEfficacy(Base):
    """
    Per-habit recovery self-efficacy score (0–10).
    Reference: SPEC-failure-layer §7.1, PRD §4.4.3.

    Single item: "If you missed this three days in a row, how confident are
    you that you'd start again?" — 0 to 10.

    Cadence: at habit creation, every 14 days, and on entry to lapsed_2.
    """
    __tablename__ = "recovery_self_efficacy"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–10
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    trigger: Mapped[str] = mapped_column(
        Enum("creation", "periodic", "lapsed_2", name="rse_trigger_enum"), nullable=False
    )


class ActionCrisisMeasure(Base):
    """
    Brandstätter's Action Crisis Scale (adapted for prototyping — see §7.2 licensing note).
    6 items, 1–7 each. instrument_version is required for §8.8 research claims.

    Cadence: every 21 days per active journey, plus on entry to lapsed_2.
    """
    __tablename__ = "action_crisis_measures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    subscale_scores: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # Which instrument wording produced this number (IRB requirement — §8.8)
    instrument_version: Mapped[str] = mapped_column(String(32), nullable=False)
