"""Habits router — CRUD for Anchor and Habit."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from src.core.deps import DB, CurrentIdentity
from src.habits import service
from src.habits.schemas import (
    AnchorCreate,
    AnchorRead,
    HabitCreate,
    HabitRead,
    HabitUpdate,
    ConflictAlertRead,
    ConflictResolveRequest,
)
from src.habits.conflict_models import ConflictAlert
from src.users.service import get_or_create_user
from src.occurrences.models import Occurrence

router = APIRouter(prefix="/habits", tags=["habits"])


# ── Anchors ───────────────────────────────────────────────────────────────────

@router.post("/anchors", response_model=AnchorRead, status_code=status.HTTP_201_CREATED)
async def create_anchor(
    body: AnchorCreate, db: DB, identity: CurrentIdentity
) -> AnchorRead:
    user = await get_or_create_user(db, identity)
    anchor = await service.create_anchor(db, user.id, body)
    return AnchorRead.model_validate(anchor)


# ── Habits ────────────────────────────────────────────────────────────────────

@router.post("", response_model=HabitRead, status_code=status.HTTP_201_CREATED)
async def create_habit(
    body: HabitCreate, db: DB, identity: CurrentIdentity
) -> HabitRead:
    user = await get_or_create_user(db, identity)
    habit = await service.create_habit(db, user.id, body)
    return HabitRead.model_validate(habit)


@router.get("", response_model=list[HabitRead])
async def list_habits(db: DB, identity: CurrentIdentity) -> list[HabitRead]:
    user = await get_or_create_user(db, identity)
    habits = await service.get_user_habits(db, user.id)
    return [HabitRead.model_validate(h) for h in habits]


# ── Conflicts ─────────────────────────────────────────────────────────────────
#
# These MUST be declared before the "/{habit_id}" routes below. FastAPI matches
# in declaration order, so with "/{habit_id}" first, a request for
# "/habits/conflicts" binds habit_id="conflicts", fails UUID validation, and
# returns 422 — never reaching this handler at all.

@router.get("/conflicts", response_model=list[ConflictAlertRead])
async def list_conflicts(db: DB, identity: CurrentIdentity) -> list[ConflictAlertRead]:
    user = await get_or_create_user(db, identity)
    from sqlalchemy import select
    result = await db.execute(
        select(ConflictAlert).where(
            ConflictAlert.user_id == user.id,
            ConflictAlert.status == "pending"
        ).order_by(ConflictAlert.detected_for_date)
    )
    alerts = result.scalars().all()
    return [ConflictAlertRead.model_validate(a) for a in alerts]


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictAlertRead)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    body: ConflictResolveRequest,
    db: DB,
    identity: CurrentIdentity,
) -> ConflictAlertRead:
    user = await get_or_create_user(db, identity)
    from sqlalchemy import select
    result = await db.execute(
        select(ConflictAlert).where(
            ConflictAlert.id == conflict_id,
            ConflictAlert.user_id == user.id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict alert not found.")
    
    if alert.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conflict already resolved.")

    if body.action == "ignore":
        alert.status = "resolved_ignore"
    elif body.action == "rest":
        alert.status = "resolved_rest"
        # preemptively skip the occurrence as "rest"
        if alert.occurrence_id:
            occ_result = await db.execute(select(Occurrence).where(Occurrence.id == alert.occurrence_id))
            occ = occ_result.scalar_one_or_none()
            if occ and occ.outcome is None:
                occ.outcome = "rest"
    elif body.action == "move":
        if not body.new_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="new_time required to move.")
        alert.status = "resolved_move"
        if alert.occurrence_id:
            occ_result = await db.execute(select(Occurrence).where(Occurrence.id == alert.occurrence_id))
            occ = occ_result.scalar_one_or_none()
            if occ and occ.outcome is None:
                occ.scheduled_local = body.new_time
                # Recalculate window based on new time (we keep the same window width)
                delta = occ.window_end - occ.window_start
                half = delta / 2
                occ.window_start = body.new_time - half
                occ.window_end = body.new_time + half
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action.")
        
    await db.commit()
    return ConflictAlertRead.model_validate(alert)


# ── Single habit ──────────────────────────────────────────────────────────────
#
# Declared last, deliberately. "/{habit_id}" is a catch-all for any single path
# segment, so anything static that lives under /habits must be registered above
# it or it will never be reached.

@router.get("/{habit_id}", response_model=HabitRead)
async def get_habit(
    habit_id: uuid.UUID, db: DB, identity: CurrentIdentity
) -> HabitRead:
    user = await get_or_create_user(db, identity)
    habit = await service.get_habit(db, habit_id, user.id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    return HabitRead.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitRead)
async def update_habit(
    habit_id: uuid.UUID,
    body: HabitUpdate,
    db: DB,
    identity: CurrentIdentity,
) -> HabitRead:
    user = await get_or_create_user(db, identity)
    habit = await service.get_habit(db, habit_id, user.id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    if body.title is not None:
        habit.title = body.title
    await db.flush()
    return HabitRead.model_validate(habit)

