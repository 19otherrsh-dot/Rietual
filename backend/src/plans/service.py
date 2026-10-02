"""Plans service."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.plans.models import Plan
from src.plans.schemas import PlanCreate


async def create_plan(
    db: AsyncSession, habit_id: uuid.UUID, data: PlanCreate
) -> Plan:
    plan = Plan(
        habit_id=habit_id,
        plan_type=data.plan_type,
        created_via=data.created_via,
        wish_text=data.wish_text,
        outcome_text=data.outcome_text,
        obstacle_text=data.obstacle_text,   # verbatim, unbounded (D6)
        obstacle_class=data.obstacle_class,
        obstacle_source=data.obstacle_source,
        outcome_imagined_seconds=data.outcome_imagined_seconds,
        obstacle_imagined_seconds=data.obstacle_imagined_seconds,
        drilldown_used=data.drilldown_used,
        plan_response_text=data.plan_response_text,
    )
    db.add(plan)
    await db.flush()

    # Update the habit's plan_id to the new plan
    from src.habits.models import Habit  # avoid circular import at module level
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalar_one_or_none()
    if habit is not None:
        habit.plan_id = plan.id

    return plan


async def supersede_plan(
    db: AsyncSession, old_plan_id: uuid.UUID, new_plan: Plan
) -> None:
    """Mark old_plan as superseded by new_plan and update the chain."""
    result = await db.execute(select(Plan).where(Plan.id == old_plan_id))
    old = result.scalar_one_or_none()
    if old is not None:
        old.superseded_by = new_plan.id


async def get_active_plan(db: AsyncSession, habit_id: uuid.UUID) -> Plan | None:
    """Return the most recent non-superseded plan for a habit."""
    result = await db.execute(
        select(Plan)
        .where(Plan.habit_id == habit_id, Plan.superseded_by.is_(None))
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
