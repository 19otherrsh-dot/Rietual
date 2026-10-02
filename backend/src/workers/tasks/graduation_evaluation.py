"""
Graduation evaluation — Habit Engine §9, DECISIONS-v1 D10.

Runs nightly. For each forming/established habit, checks all three criteria and
transitions the ones that meet them.

The rules live in `ritual.engine.graduation`; this task is persistence and
transition only. In particular the completion denominator — probe-eligible
occurrences, not all occurrences — is the core's business, because getting it
wrong here would let a habit graduate on the strength of us having stopped
prompting rather than on anything the user did.

D10: "Whatever graduation costs in subscription months, the alternative is a
product with a structural interest in the user never succeeding."
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from ritual.engine.graduation import SRBAIMeasure, check_graduation
from ritual.engine.models import FadeLevel, HabitState, Occurrence, Outcome, PromptPolicy
from src.workers.celery_app import celery_app

#: How far back to load occurrences. The rule reads 30 days; we fetch a little
#: more so a boundary occurrence is never silently dropped by clock skew.
_LOOKBACK = timedelta(days=35)


@celery_app.task(name="src.workers.tasks.graduation_evaluation.evaluate_graduation")
def evaluate_graduation() -> dict:
    return asyncio.run(_async_evaluate())


def _to_core_occurrence(row) -> Occurrence:
    """Map an ORM row onto the core's Occurrence.

    Only the fields the graduation rule reads are populated; window bounds are
    irrelevant to it and are filled from the scheduled time rather than
    invented.
    """
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
        prompt_delivered_at=getattr(row, "prompt_delivered_at", None),
        completed_at=row.completed_at,
        outcome=outcome,
    )


async def _async_evaluate() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.habits.models import Habit
    from src.instruments.models import SRBAIMeasurement
    from src.occurrences.models import Occurrence as OccurrenceRow

    now = datetime.now(timezone.utc)
    graduated = 0
    checked = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Habit).where(Habit.state.in_(["forming", "established"]))
        )
        habits = list(result.scalars().all())

        for habit in habits:
            checked += 1

            # Criterion 2 is the cheapest to evaluate, so short-circuit on it.
            # A habit still being prompted cannot graduate, and loading its
            # measures and month of occurrences to discover that is wasteful.
            if habit.fade_level < int(FadeLevel.L4):
                continue

            measure_rows = await db.execute(
                select(SRBAIMeasurement)
                .where(SRBAIMeasurement.habit_id == habit.id)
                .order_by(SRBAIMeasurement.measured_at.desc())
                .limit(4)
            )
            measures = [
                SRBAIMeasure(measured_at=m.measured_at, mean_score=m.mean_score)
                for m in measure_rows.scalars().all()
            ]

            occ_rows = await db.execute(
                select(OccurrenceRow).where(
                    OccurrenceRow.habit_id == habit.id,
                    OccurrenceRow.scheduled_local >= now - _LOOKBACK,
                )
            )
            occurrences = [_to_core_occurrence(o) for o in occ_rows.scalars().all()]

            check = check_graduation(
                state=HabitState(habit.state),
                fade_level=FadeLevel(habit.fade_level),
                measures=measures,
                occurrences=occurrences,
                now=now,
            )

            if not check.eligible:
                continue

            habit.state = HabitState.GRADUATED.value
            habit.graduated_at = now
            graduated += 1

        await db.commit()

    return {"checked": checked, "graduated": graduated}
