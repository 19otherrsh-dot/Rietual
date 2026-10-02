"""
Reminder fading evaluation — Habit Engine §5.2.

Advance one level after 3 **consecutive** unprompted completions.
Regress one level on entry to lapsed_2 (never to L0 — handled in the service
when the state transition happens, not here).

The advancement rule is delegated to `ritual.engine.fading.should_advance`.
The previous implementation loaded the last three *completed* occurrences and
checked they were unprompted, which is not the same thing: it ignored anything
that happened between them. A habit going complete, miss, complete, miss,
complete would advance a fade level on the strength of three completions with
two misses interleaved — fading a user's prompts down at exactly the moment
their evidence says they still need them.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from ritual.engine.fading import advance, should_advance
from ritual.engine.models import FadeLevel, HabitState, Occurrence, Outcome, PromptPolicy
from src.workers.celery_app import celery_app

#: Enough history to see a streak plus whatever broke it.
_LOOKBACK = timedelta(days=21)


@celery_app.task(name="src.workers.tasks.fade_evaluation.evaluate_fading")
def evaluate_fading() -> dict:
    return asyncio.run(_async_evaluate())


def _to_core_occurrence(row) -> Occurrence:
    outcome = Outcome.PENDING
    if row.outcome is not None:
        try:
            outcome = Outcome(row.outcome)
        except ValueError:
            outcome = Outcome.PENDING
    return Occurrence(
        id=str(row.id),
        habit_id=str(row.habit_id),
        scheduled_local=row.scheduled_local,
        window_start=row.window_start,
        window_end=row.window_end,
        prompt_policy=PromptPolicy(row.prompt_policy),
        prompt_delivered_at=row.prompt_delivered_at,
        completed_at=row.completed_at,
        outcome=outcome,
    )


async def _async_evaluate() -> dict:
    from sqlalchemy import select

    from ritual.engine.models import Habit as CoreHabit
    from src.core.database import AsyncSessionLocal
    from src.habits.models import Habit
    from src.occurrences.models import Occurrence as OccurrenceRow

    now = datetime.now(timezone.utc)
    advanced = 0
    checked = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Habit).where(Habit.state.in_(["forming", "established"]))
        )
        habits = list(result.scalars().all())

        for habit in habits:
            checked += 1
            if habit.fade_level >= int(FadeLevel.L4):
                continue

            # Most recent first, and *unfiltered* by outcome: the rule needs to
            # see the misses, not just the completions.
            occ_result = await db.execute(
                select(OccurrenceRow)
                .where(
                    OccurrenceRow.habit_id == habit.id,
                    OccurrenceRow.scheduled_local >= now - _LOOKBACK,
                    OccurrenceRow.outcome.is_not(None),
                )
                .order_by(OccurrenceRow.scheduled_local.desc())
                .limit(20)
            )
            recent = [_to_core_occurrence(o) for o in occ_result.scalars().all()]

            core_habit = CoreHabit(
                id=str(habit.id),
                user_id=str(habit.user_id),
                title=habit.title,
                full_version=habit.full_version,
                micro_version=habit.micro_version,
                anchor_id=str(habit.anchor_id) if habit.anchor_id else "",
                timezone="UTC",
                state=HabitState(habit.state),
                fade_level=FadeLevel(habit.fade_level),
            )

            if should_advance(core_habit, recent):
                habit.fade_level = int(advance(FadeLevel(habit.fade_level)))
                advanced += 1

        await db.commit()

    return {"checked": checked, "advanced": advanced}
