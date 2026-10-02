"""Plans router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from src.core.deps import DB, CurrentIdentity
from src.habits.service import get_habit
from src.plans import service
from src.plans.schemas import PlanCreate, PlanRead
from src.users.service import get_or_create_user

router = APIRouter(prefix="/habits", tags=["plans"])


@router.post(
    "/{habit_id}/plans",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    habit_id: uuid.UUID,
    body: PlanCreate,
    db: DB,
    identity: CurrentIdentity,
) -> PlanRead:
    user = await get_or_create_user(db, identity)
    habit = await get_habit(db, habit_id, user.id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    plan = await service.create_plan(db, habit_id, body)
    return PlanRead.model_validate(plan)


@router.get("/{habit_id}/plans/active", response_model=PlanRead)
async def get_active_plan(
    habit_id: uuid.UUID,
    db: DB,
    identity: CurrentIdentity,
) -> PlanRead:
    user = await get_or_create_user(db, identity)
    habit = await get_habit(db, habit_id, user.id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    plan = await service.get_active_plan(db, habit_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan.")
    return PlanRead.model_validate(plan)
