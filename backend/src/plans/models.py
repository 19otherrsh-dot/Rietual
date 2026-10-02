"""
Plan ORM model — WOOP and if-then plans.

Reference: SPEC-onboarding-v1 §8 (data model), DECISIONS-v1 D5, D6.

Critical design constraints:
  - obstacle_text is TEXT with no length limit (D6). Never truncate.
  - plan_type distinguishes woop from if_then — prevents counting
    if-then plans as mental contrasting in metrics (Onboarding §8 note).
  - WOOP fields are null for if_then plans — not defaulted to empty strings.
  - superseded_by enables the chain of WOOP re-runs (§3.5).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from src.core.types import UUID  # portable: native uuid on Postgres, CHAR(32) elsewhere
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Plan type (D5) ────────────────────────────────────────────────────────
    plan_type: Mapped[str] = mapped_column(
        Enum("woop", "if_then", name="plan_type_enum"), nullable=False
    )
    # How the plan was created (for metric segmentation — Onboarding §9)
    created_via: Mapped[str] = mapped_column(
        Enum(
            "onboarding_proper",
            "onboarding_quick",
            "first_lapse",         # D5: WOOP offered at first lapse for if_then users
            "replanning",
            name="plan_created_via_enum",
        ),
        nullable=False,
    )

    # ── WOOP fields (null for if_then plans) ──────────────────────────────────
    wish_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # obstacle_text: TEXT, unbounded, stored VERBATIM (D6).
    # This field is quoted back at the worst moment of the user's week.
    # Their sentence does the work; our truncation does not.
    obstacle_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    obstacle_class: Mapped[str | None] = mapped_column(
        Enum("internal", "external_accepted", name="obstacle_class_enum"), nullable=True
    )
    obstacle_source: Mapped[str | None] = mapped_column(
        Enum("freetext", "picker", "after_drilldown", name="obstacle_source_enum"),
        nullable=True,
    )

    # Imagining durations (seconds) — the mechanism, not decoration.
    # Should read ~15 each in proper path. Shortfall indicates a skip leaked in.
    # (Onboarding §8 note — "their job is now to catch backgrounding, force-quits")
    outcome_imagined_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    obstacle_imagined_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    drilldown_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Common field (both plan types) ───────────────────────────────────────
    # "If [obstacle], then I will ___"
    plan_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Chain of re-runs (§3.5 — WOOP is a transferable skill, re-runnable)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True
    )
