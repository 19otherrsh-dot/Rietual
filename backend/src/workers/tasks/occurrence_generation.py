"""
Occurrence generation Celery task — Habit Engine §4.1.

Materializes occurrences 7 days ahead.
Handles DST transitions and timezone changes (§4.2–§4.3).

DST resolution is delegated to `ritual.engine.scheduling.resolve_local`, which
is covered by the gate suite in `tests/test_engine.py`. The previous pytz
implementation had a confirmed defect on the spring-forward gap:

    tz.localize(datetime(2026, 3, 29, 1, 30), is_dst=True)
      -> stored 2026-03-29 00:30+00:00, which renders locally as 00:30

i.e. the occurrence moved an hour *earlier* than intended rather than forward
through the gap — and 00:30 is inside the 22:00–07:00 quiet window. Narrow
blast radius (one day a year, only anchors whose nominal time falls inside the
gap hour) but exactly the class of bug PLAN §7 gates on.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ritual.engine.scheduling import resolve_local
from src.workers.celery_app import celery_app


@celery_app.task(name="src.workers.tasks.occurrence_generation.generate_occurrences")
def generate_occurrences() -> dict:
    return asyncio.run(_async_generate())


async def _async_generate() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.habits.models import Anchor, Habit
    from src.occurrences.models import Occurrence

    now_utc = datetime.now(timezone.utc)
    horizon = now_utc + timedelta(days=7)
    generated = 0

    from src.habits.chains import suppressed_habit_ids

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Habit).where(
                Habit.state.in_(["forming", "established", "lapsed_1", "lapsed_2"])
            )
        )
        habits = list(result.scalars().all())

        # Resolve chain suppression once per anchor rather than per occurrence.
        # Chains are implicit: habits sharing an anchor, ordered by
        # chain_position (§7). Only the head may be prompted.
        by_anchor: dict = {}
        for h in habits:
            if h.anchor_id is not None:
                by_anchor.setdefault(h.anchor_id, []).append(h)
        suppressed: set[str] = set()
        for anchor_id, rows in by_anchor.items():
            suppressed |= suppressed_habit_ids(anchor_id, rows)

        for habit in habits:
            if habit.anchor_id is None:
                continue

            anchor_result = await db.execute(
                select(Anchor).where(Anchor.id == habit.anchor_id)
            )
            anchor = anchor_result.scalar_one_or_none()
            if anchor is None or anchor.nominal_time is None:
                continue

            # Fetch user timezone
            from src.users.models import User
            user_result = await db.execute(
                select(User).where(User.id == habit.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                continue

            try:
                tz = ZoneInfo(user.timezone)
            except Exception:
                tz = ZoneInfo("UTC")

            # Check if occurrence already exists for today+7 days
            existing_result = await db.execute(
                select(Occurrence.scheduled_local).where(
                    Occurrence.habit_id == habit.id,
                    Occurrence.scheduled_local >= now_utc,
                )
            )
            existing_times = {r for r in existing_result.scalars()}

            # Generate daily occurrences over the 7-day window
            current_day = now_utc.astimezone(tz).date()
            for i in range(7):
                target_date = current_day + timedelta(days=i)
                # Wall-clock: always 07:00 stays 07:00 through DST (§4.2).
                # resolve_local shifts forward through a spring-forward gap and
                # takes the first instant of an ambiguous fall-back hour, so a
                # habit never vanishes and never fires twice.
                local_naive = datetime.combine(target_date, anchor.nominal_time)
                local_aware = resolve_local(local_naive, tz)

                utc_time = local_aware.astimezone(timezone.utc)

                if utc_time in existing_times or utc_time < now_utc:
                    continue

                # Window: ±90 min for stable anchors, ±3h for variable/unstable
                window_minutes = 90 if anchor.stability == "stable" else 180
                window_delta = timedelta(minutes=window_minutes)

                occ = Occurrence(
                    habit_id=habit.id,
                    scheduled_local=utc_time,
                    user_timezone=user.timezone,
                    window_start=utc_time - window_delta,
                    window_end=utc_time + window_delta,
                    # Chain members other than the head are never prompted
                    # (§7). Suppressing here rather than at dispatch keeps
                    # probe assignment from later picking a tail link as a
                    # probe day, which would "withhold" a prompt that was
                    # never going to be sent and quietly corrupt the
                    # unprompted-completion metric.
                    prompt_policy=(
                        "suppress" if str(habit.id) in suppressed else "prompt"
                    ),
                )
                db.add(occ)
                generated += 1

        await db.commit()

    return {"generated": generated}
