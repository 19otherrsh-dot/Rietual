"""Failure Layer router — recovery break and self-efficacy endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.deps import DB, CurrentIdentity
from src.failure_layer import service as fl_service
from src.failure_layer.models import RecoverySelfEfficacy
from src.habits.service import get_habit
from src.users.service import get_or_create_user

router = APIRouter(prefix="/habits", tags=["failure-layer"])


class RecoverySelfEfficacyCreate(BaseModel):
    score: int      # 0–10
    trigger: str    # creation | periodic | lapsed_2


class RecoverySelfEfficacyRead(BaseModel):
    id: uuid.UUID
    habit_id: uuid.UUID
    score: int
    trigger: str
    model_config = {"from_attributes": True}


class HabitStateRead(BaseModel):
    habit_id: uuid.UUID
    state: str
    # NOTE: cue-stability data is deliberately NOT included here (D11).
    # Stability is surfaced at habit creation/re-planning only,
    # never in any surface that follows a miss.


@router.get("/{habit_id}/state", response_model=HabitStateRead)
async def get_habit_state(
    habit_id: uuid.UUID,
    db: DB,
    identity: CurrentIdentity,
) -> HabitStateRead:
    user = await get_or_create_user(db, identity)
    habit = await get_habit(db, habit_id, user.id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    return HabitStateRead(habit_id=habit.id, state=habit.state)


@router.post("/{habit_id}/recovery-self-efficacy", response_model=RecoverySelfEfficacyRead)
async def record_rse(
    habit_id: uuid.UUID,
    body: RecoverySelfEfficacyCreate,
    db: DB,
    identity: CurrentIdentity,
) -> RecoverySelfEfficacyRead:
    user = await get_or_create_user(db, identity)
    habit = await get_habit(db, habit_id, user.id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    if not (0 <= body.score <= 10):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Score must be between 0 and 10.",
        )
    rse = await fl_service.record_recovery_self_efficacy(
        db, habit_id, body.score, body.trigger
    )
    return RecoverySelfEfficacyRead.model_validate(rse)
