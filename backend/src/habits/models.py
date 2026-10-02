"""
Habit Engine — Anchor and Habit ORM models.

Reference: SPEC-habit-engine-v1 §1 (object model), §2 (anchors), §3 (stability).

Key invariants enforced here:
  - micro_version is mandatory at creation (§1 — "defined calmly on day one")
  - stability_basis is always explicit (prior/calendar/observed); never implied
  - fade_level is 0–4 (L0=all prompted, L4=no prompts)
"""
from __future__ import annotations

import uuid
from datetime import datetime, time, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from src.core.types import UUID  # portable: native uuid on Postgres, CHAR(32) elsewhere
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

# ── Enums ─────────────────────────────────────────────────────────────────────

AnchorClass = Enum(
    "wake",
    "first_coffee",
    "commute_start",
    "lunch",
    "work_end",
    "dinner",
    "bedtime",
    "custom",
    name="anchor_class_enum",
)

StabilityLevel = Enum(
    "stable",
    "variable",
    "unstable",
    "unscored",          # < 5 observations — honest label (Habit Engine §3.2)
    name="stability_level_enum",
)

StabilityBasis = Enum(
    "prior",             # cold-start default from §3.4 class priors
    "calendar",          # derived from calendar permission
    "observed",          # from actual completion timestamps
    name="stability_basis_enum",
)

HabitState = Enum(
    "forming",
    "established",
    "graduated",
    "lapsed_1",
    "lapsed_2",
    "dormant",
    "paused",
    "retired",
    name="habit_state_enum",
)


# ── Anchor ────────────────────────────────────────────────────────────────────

class Anchor(Base):
    """
    Cue object.  Multiple habits may share one anchor (stacking — §7).
    Stability is recomputed nightly by the Celery stability_scoring task.
    """
    __tablename__ = "anchors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anchor_class: Mapped[str] = mapped_column(AnchorClass, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)

    # Wall-clock time the anchor nominally occurs (null for event-based anchors).
    # Stored as local time; timezone is on the User row.
    nominal_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    stability: Mapped[str] = mapped_column(
        StabilityLevel, default="unscored", nullable=False
    )
    stability_basis: Mapped[str] = mapped_column(
        StabilityBasis, default="prior", nullable=False
    )

    # Temporal stability dimension (circular MAD, minutes) — Habit Engine §3.1
    temporal_mad_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Locational stability (share in modal cluster) — computed on-device, sent as float
    locational_cluster_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Calendar stability (share of days with same free/busy shape)
    calendar_shape_share: Mapped[float | None] = mapped_column(Float, nullable=True)

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

    habits: Mapped[list["Habit"]] = relationship("Habit", back_populates="anchor")


# ── Habit ─────────────────────────────────────────────────────────────────────

class Habit(Base):
    """
    Core behavioral object.  The onboarding spec hands off a habit with a plan;
    the habit engine owns everything between creation and graduation.
    """
    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint("fade_level BETWEEN 0 AND 4", name="ck_fade_level_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    journey_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    title: Mapped[str] = mapped_column(String(256), nullable=False)

    # Both versions are mandatory at creation — never improvised post-failure.
    # Habit Engine §1: "The two-minute version defined calmly on day one is a
    # different and much better artifact than one improvised at the bottom of a bad week."
    full_version: Mapped[str] = mapped_column(Text, nullable=False)
    micro_version: Mapped[str] = mapped_column(Text, nullable=False)  # 2-min version

    anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("anchors.id", ondelete="SET NULL"), nullable=True
    )
    # habits.plan_id -> plans.id and plans.habit_id -> habits.id form a cycle,
    # so one side must be created by a later ALTER or neither table can be
    # emitted first. We break it here rather than on plans.habit_id because
    # plans authoritatively belong to a habit; this column is the convenience
    # pointer to the *current* plan. Without use_alter, create_all and
    # migrations both stall on the unresolvable ordering.
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "plans.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_habits_current_plan_id",
        ),
        nullable=True,
    )

    state: Mapped[str] = mapped_column(HabitState, default="forming", nullable=False)

    # Reminder fading ladder L0–L4 (Habit Engine §5.1)
    fade_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Chain membership (Habit Engine §7) — position in the stack.
    # A chain is implicit: the habits sharing an anchor, ordered by this
    # column. Position 0 is the head, and the head is the ONLY member that may
    # carry a prompt — see ritual.engine.chains.prompt_target. Prompting each
    # link separately is not a smaller version of stacking, it is the absence
    # of it: the user stops being cued by finishing the previous action.
    chain_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Set when the habit graduates (Habit Engine §9, D10). Drives the day-30
    # and day-90 maintenance checks and nothing else — graduation stops
    # prompting permanently and is never reversed on our initiative.
    graduated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Pause metadata
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_reason: Mapped[str | None] = mapped_column(
        Enum("transition", "user", "illness", "pause_clause", name="pause_reason_enum"),
        nullable=True,
    )

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

    anchor: Mapped[Anchor | None] = relationship("Anchor", back_populates="habits")
