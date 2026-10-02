"""
Instrument measurement storage.

Reference: PRD §4.6.1, Habit Engine §9.

Only SRBAI is stored per-habit — it is the automaticity measure that gates
graduation, and automaticity is a property of one habit rather than of a
person. The other instruments in the Phase 1 battery (WHO-5, MCTQ, BREQ-3,
PSS-10) are per-user and belong on their own schedule.

`instrument_version` is recorded because §8.8 research claims need to know
which wording produced which number. It costs one column now and is
unrecoverable later.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.types import UUID


class SRBAIMeasurement(Base):
    """One SRBAI response for one habit.

    Two consecutive measures at or above threshold is criterion 1 of three for
    graduation (Habit Engine §9.1). "Consecutive" is evaluated over these rows
    ordered by `measured_at`, so a measure is never overwritten — a later
    passing score does not erase an earlier failing one.
    """

    __tablename__ = "srbai_measurements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: The four raw item scores, 1-7 each.
    raw_scores: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    mean_score: Mapped[float] = mapped_column(Float, nullable=False)

    instrument_version: Mapped[str] = mapped_column(
        String(32), default="SRBAI-4-2012", nullable=False
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
