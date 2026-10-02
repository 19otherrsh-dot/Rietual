"""Habits service."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.habits.models import Anchor, Habit
from src.habits.schemas import AnchorCreate, HabitCreate


async def create_anchor(
    db: AsyncSession, user_id: uuid.UUID, data: AnchorCreate
) -> Anchor:
    anchor = Anchor(
        user_id=user_id,
        anchor_class=data.anchor_class,
        label=data.label,
        nominal_time=data.nominal_time,
        stability="unscored",
        stability_basis="prior",
    )
    db.add(anchor)
    await db.flush()
    return anchor


async def create_habit(
    db: AsyncSession, user_id: uuid.UUID, data: HabitCreate
) -> Habit:
    habit = Habit(
        user_id=user_id,
        title=data.title,
        full_version=data.full_version,
        micro_version=data.micro_version,
        anchor_id=data.anchor_id,
        journey_id=data.journey_id,
        state="forming",
        fade_level=0,
    )
    db.add(habit)
    await db.flush()
    return habit


async def get_user_habits(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Habit]:
    result = await db.execute(
        select(Habit)
        .where(Habit.user_id == user_id)
        .order_by(Habit.created_at)
    )
    return list(result.scalars().all())


async def get_habit(
    db: AsyncSession, habit_id: uuid.UUID, user_id: uuid.UUID
) -> Habit | None:
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    )
    return result.scalar_one_or_none()
