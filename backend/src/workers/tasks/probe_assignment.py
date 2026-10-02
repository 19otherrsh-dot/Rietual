"""
Probe day assignment — Habit Engine §5.3.

One occurrence per habit per week is designated a probe (prompt withheld).
This is the only way to measure unprompted completion at L0–L1: without
withholding we cannot distinguish "completed because we reminded them" from
"would have completed anyway", and that distinction is the primary success
metric.

Because a probe is deliberately withholding help from a user, all five fences
are enforced here, at materialisation. A fence checked at fire time is a fence
that gets skipped under a deadline.

  1. Never during lapsed_*, dormant, or paused states
  2. Never in a habit's first 7 days
  3. Maximum 1 per habit per week
  4. Maximum 2 per user per week across all habits
  5. Never on the same weekday slot two consecutive weeks

And the sixth rule, enforced downstream in miss detection: a probe miss is
recorded as a probe miss and does NOT count toward lapse progression or streak
loss. We caused it, so we absorb it.

Fences 3 and 5 were previously unimplemented — the code picked uniformly at
random from all prompted occurrences, so a user could be probed on the same
weekday indefinitely. Limits now come from `ritual.engine.fading` so the worker
and the domain core cannot drift apart.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ritual.engine.fading import (
    MAX_PROBES_PER_HABIT_PER_WEEK,
    MAX_PROBES_PER_USER_PER_WEEK,
    PROBE_MIN_HABIT_AGE,
)
from ritual.engine.models import FadeLevel
from src.workers.celery_app import celery_app

#: How far back to look for a previous probe when applying fence 5.
_PREVIOUS_PROBE_LOOKBACK = timedelta(days=14)


@celery_app.task(name="src.workers.tasks.probe_assignment.assign_probe_days")
def assign_probe_days() -> dict:
    return asyncio.run(_async_assign())


def _local_weekday(occurrence, fallback_tz: str = "UTC") -> int | None:
    """Weekday in the user's local zone, since that is what they experience."""
    try:
        tz = ZoneInfo(occurrence.user_timezone or fallback_tz)
    except Exception:
        return None
    return int(occurrence.scheduled_local.astimezone(tz).weekday())


async def _async_assign() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.habits.models import Habit
    from src.occurrences.models import Occurrence

    now = datetime.now(timezone.utc)
    week_ahead = now + timedelta(days=7)
    assigned = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        user_probe_count: dict[str, int] = {}

        # Fences 1 and 2, at the query.
        habits_result = await db.execute(
            select(Habit).where(
                Habit.state.in_(["forming", "established"]),
                Habit.created_at <= now - PROBE_MIN_HABIT_AGE,
            )
        )
        habits = list(habits_result.scalars().all())

        for habit in habits:
            uid = str(habit.user_id)

            # Fence 4 — per-user weekly cap.
            if user_probe_count.get(uid, 0) >= MAX_PROBES_PER_USER_PER_WEEK:
                skipped += 1
                continue

            # Nothing to withhold once prompting has stopped.
            if habit.fade_level >= int(FadeLevel.L4):
                skipped += 1
                continue

            # Fence 3 — one per habit per week. Guards against a re-run of this
            # task double-probing the same horizon.
            already_result = await db.execute(
                select(Occurrence).where(
                    Occurrence.habit_id == habit.id,
                    Occurrence.scheduled_local >= now,
                    Occurrence.scheduled_local <= week_ahead,
                    Occurrence.prompt_policy == "probe",
                )
            )
            if len(list(already_result.scalars().all())) >= MAX_PROBES_PER_HABIT_PER_WEEK:
                skipped += 1
                continue

            # Fence 5 — the weekday of the most recent probe is off limits.
            previous_result = await db.execute(
                select(Occurrence)
                .where(
                    Occurrence.habit_id == habit.id,
                    Occurrence.prompt_policy == "probe",
                    Occurrence.scheduled_local >= now - _PREVIOUS_PROBE_LOOKBACK,
                    Occurrence.scheduled_local < now,
                )
                .order_by(Occurrence.scheduled_local.desc())
                .limit(1)
            )
            previous = previous_result.scalar_one_or_none()
            blocked_weekday = _local_weekday(previous) if previous is not None else None

            occ_result = await db.execute(
                select(Occurrence)
                .where(
                    Occurrence.habit_id == habit.id,
                    Occurrence.scheduled_local >= now,
                    Occurrence.scheduled_local <= week_ahead,
                    Occurrence.prompt_policy == "prompt",
                    Occurrence.outcome.is_(None),
                )
                .order_by(Occurrence.scheduled_local)
            )
            candidates = [
                o
                for o in occ_result.scalars().all()
                if blocked_weekday is None or _local_weekday(o) != blocked_weekday
            ]

            if not candidates:
                skipped += 1
                continue

            chosen = random.choice(candidates)
            chosen.prompt_policy = "probe"
            user_probe_count[uid] = user_probe_count.get(uid, 0) + 1
            assigned += 1

        await db.commit()

    return {"assigned": assigned, "skipped": skipped}
