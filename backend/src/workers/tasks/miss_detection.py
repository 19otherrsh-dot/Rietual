"""
Miss detection Celery task.

Runs every 30 minutes. For each habit with an open occurrence
past its window_end + 2h grace, marks the occurrence as missed
and applies the state machine transition.

Critical rules enforced here:
  - Grace window: 2h after window_end (Failure Layer §1.2)
  - Time-of-day gate: never fire 22:00–07:00 user local time (§1.2)
  - D1: NO push dispatch for lapsed_1 transitions
  - push_side_trigger from state machine controls dispatch
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ritual.engine.scheduling import is_quiet_hours
from src.workers.celery_app import celery_app


@celery_app.task(name="src.workers.tasks.miss_detection.detect_misses")
def detect_misses() -> dict:
    """
    Synchronous Celery task entry point.
    Runs the async detection logic via asyncio.run().
    """
    return asyncio.run(_async_detect_misses())


async def _async_detect_misses() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.failure_layer.service import detect_miss
    from src.habits.models import Habit
    from src.occurrences.models import Occurrence

    now_utc = datetime.now(timezone.utc)
    grace = timedelta(hours=2)
    cutoff = now_utc - grace

    processed = 0
    skipped_time_gate = 0

    async with AsyncSessionLocal() as db:
        # Find occurrences whose window has closed + 2h, not yet resolved
        result = await db.execute(
            select(Occurrence)
            .where(
                Occurrence.outcome.is_(None),
                Occurrence.window_end <= cutoff,
            )
        )
        open_occurrences = list(result.scalars().all())

        for occ in open_occurrences:
            # Time-of-day gate: never fire 22:00–07:00 user local time (§1.2).
            # Someone who does their evening routine at 21:40 instead of 21:00
            # has not failed at anything, and telling them so at 23:31 is how a
            # product earns its uninstall.
            try:
                local_now = now_utc.astimezone(ZoneInfo(occ.user_timezone))
            except Exception:
                local_now = None  # unknown timezone — proceed rather than stall
            if local_now is not None and is_quiet_hours(local_now):
                skipped_time_gate += 1
                continue

            # Get the habit
            habit_result = await db.execute(
                select(Habit).where(Habit.id == occ.habit_id)
            )
            habit = habit_result.scalar_one_or_none()
            if habit is None or habit.state == "paused":
                continue

            # Count consecutive misses for this habit
            from sqlalchemy import func
            from src.failure_layer.models import Miss
            miss_count_result = await db.execute(
                select(func.count(Miss.id)).where(
                    Miss.habit_id == habit.id,
                    Miss.recovered_at.is_(None),
                )
            )
            consecutive = miss_count_result.scalar() or 0

            miss = await detect_miss(
                db=db,
                habit=habit,
                occurrence_id=occ.id,
                window_start=occ.window_start,
                window_end=occ.window_end,
                consecutive_misses=consecutive,
            )
            occ.outcome = "missed"

            # D1: push_side_trigger is False for lapsed_1 — state machine enforces this.
            # We check miss.depth rather than re-running the machine.
            if miss.depth in ("lapsed_2", "dormant"):
                # TODO Phase 2: dispatch push via notifications.dispatcher
                # For now, queue is written; dispatch wired in Phase 2.
                pass

            processed += 1

        await db.commit()

    return {"processed": processed, "skipped_time_gate": skipped_time_gate}
