"""
User model.

One row per RITUAL user, keyed to their Kratos identity.
ELM track and chronotype are set during onboarding (SPEC-onboarding §5.1, §5.2).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from src.core.types import UUID  # portable: native uuid on Postgres, CHAR(32) elsewhere
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ELMTrack(str):
    CENTRAL = "central"
    PERIPHERAL = "peripheral"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kratos_identity_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    # Onboarding §5.1 ELM routing
    elm_track: Mapped[str | None] = mapped_column(
        Enum("central", "peripheral", name="elm_track_enum"), nullable=True
    )
    # Readiness item from ELM screener (item 3 — not used for routing, logged for D7 analysis)
    elm_readiness: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # IANA timezone, set during anchor selection
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

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


class CalendarBlock(Base):
    """
    Anonymous busy block synced from the client.
    We never store meeting names or attendees — only busy periods (Habit Engine §8).
    """
    __tablename__ = "calendar_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

