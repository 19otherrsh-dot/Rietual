"""
Failure Layer service — DB-side operations.

The state machine (state_machine.py) is pure logic.
This module applies transitions to the database and creates the audit trail.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.failure_layer.models import HabitStateLog, Miss, RecoverySelfEfficacy
from src.failure_layer.state_machine import HabitEvent, HabitStateEnum, transition
from src.habits.models import Habit


async def apply_event(
    db: AsyncSession,
    habit: Habit,
    event: HabitEvent,
    consecutive_misses: int = 0,
) -> tuple[HabitStateEnum, bool, bool]:
    """
    Apply a state machine event to a habit.

    Returns (new_state, push_side_trigger, recovery_break).
    Caller is responsible for dispatching push if push_side_trigger is True.
    """
    current = HabitStateEnum(habit.state)
    result = transition(current, event, consecutive_misses)

    # Write state transition log
    log = HabitStateLog(
        habit_id=habit.id,
        state=result.new_state.value,
        previous_state=current.value,
        event=event.value,
        note=result.note,
    )
    db.add(log)

    # Update habit state
    habit.state = result.new_state.value
    await db.flush()

    return result.new_state, result.push_side_trigger, result.recovery_break


async def detect_miss(
    db: AsyncSession,
    habit: Habit,
    occurrence_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
    consecutive_misses: int,
) -> Miss:
    """
    Called by the miss_detection Celery task after the grace window expires.
    Creates the Miss record and transitions the habit state.
    """
    depth_map = {
        "forming": "lapsed_1",
        "established": "lapsed_1",
        "lapsed_1": "lapsed_2",
        "lapsed_2": "lapsed_2",
    }
    depth = depth_map.get(habit.state, "lapsed_1")

    miss = Miss(
        habit_id=habit.id,
        scheduled_occurrence_id=occurrence_id,
        window_start=window_start,
        window_end=window_end,
        depth=depth,
    )
    db.add(miss)

    await apply_event(db, habit, HabitEvent.MISS, consecutive_misses)
    return miss


async def mark_recovery(
    db: AsyncSession,
    habit: Habit,
    miss: Miss,
) -> None:
    """
    Called when a completion arrives within 72h of a miss.
    Updates the Miss record and transitions the habit back to forming.
    """
    miss.recovered_at = datetime.now(timezone.utc)
    await apply_event(db, habit, HabitEvent.COMPLETION)


async def record_recovery_self_efficacy(
    db: AsyncSession,
    habit_id: uuid.UUID,
    score: int,
    trigger: str,
) -> RecoverySelfEfficacy:
    rse = RecoverySelfEfficacy(
        habit_id=habit_id,
        score=score,
        trigger=trigger,
    )
    db.add(rse)
    await db.flush()
    return rse


async def get_open_misses(
    db: AsyncSession,
    habit_id: uuid.UUID,
    within_hours: int = 72,
) -> list[Miss]:
    """Return unrecovered misses within the recovery window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    result = await db.execute(
        select(Miss)
        .where(
            Miss.habit_id == habit_id,
            Miss.recovered_at.is_(None),
            Miss.detected_at >= cutoff,
        )
        .order_by(Miss.detected_at)
    )
    return list(result.scalars().all())
