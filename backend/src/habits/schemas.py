"""Habits schemas."""
from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, field_validator


class AnchorCreate(BaseModel):
    anchor_class: str
    label: str
    nominal_time: time | None = None


class AnchorRead(BaseModel):
    id: uuid.UUID
    anchor_class: str
    label: str
    nominal_time: time | None
    stability: str
    stability_basis: str
    model_config = {"from_attributes": True}


class HabitCreate(BaseModel):
    title: str
    full_version: str
    micro_version: str  # mandatory — Habit Engine §1
    anchor_id: uuid.UUID | None = None
    journey_id: uuid.UUID | None = None

    @field_validator("micro_version")
    @classmethod
    def micro_version_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(
                "micro_version is mandatory at creation. "
                "Define the 2-minute version now, not after a failure."
            )
        return v


class HabitRead(BaseModel):
    id: uuid.UUID
    title: str
    full_version: str
    micro_version: str
    state: str
    fade_level: int
    anchor_id: uuid.UUID | None
    plan_id: uuid.UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class HabitUpdate(BaseModel):
    title: str | None = None
    state: str | None = None
    paused_reason: str | None = None


class ConflictAlertRead(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID | None
    conflict_type: str
    description: str
    status: str
    detected_for_date: datetime
    model_config = {"from_attributes": True}


class ConflictResolveRequest(BaseModel):
    action: str  # 'move', 'rest', 'ignore'
    new_time: datetime | None = None  # required if action == 'move'

