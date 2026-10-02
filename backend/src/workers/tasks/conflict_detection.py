"""
Conflict detection Celery task.

Runs nightly to detect hard and soft scheduling conflicts over a 7-day horizon.
Habit Engine §8.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from src.workers.celery_app import celery_app


@celery_app.task(name="src.workers.tasks.conflict_detection.detect_conflicts")
def detect_conflicts() -> dict:
    return asyncio.run(_async_detect_conflicts())


async def _async_detect_conflicts() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.habits.conflict_models import ConflictAlert
    from src.occurrences.models import Occurrence
    from src.users.models import CalendarBlock, User

    now_utc = datetime.now(timezone.utc)
    horizon = now_utc + timedelta(days=7)

    detected_hard = 0
    detected_soft = 0

    async with AsyncSessionLocal() as db:
        # Get all users with active habits
        users_result = await db.execute(select(User))
        users = list(users_result.scalars().all())

        for user in users:
            # 1. Fetch upcoming occurrences
            occ_result = await db.execute(
                select(Occurrence)
                .where(
                    Occurrence.scheduled_local >= now_utc,
                    Occurrence.scheduled_local <= horizon,
                    Occurrence.outcome.is_(None)
                )
                .order_by(Occurrence.scheduled_local)
            )
            # Filter in memory for this user's occurrences since habit_id links to user_id
            # But let's just do it properly
            from src.habits.models import Habit
            user_habits_result = await db.execute(
                select(Habit.id).where(Habit.user_id == user.id)
            )
            user_habit_ids = [h for h in user_habits_result.scalars()]
            if not user_habit_ids:
                continue
            
            occ_result = await db.execute(
                select(Occurrence)
                .where(
                    Occurrence.habit_id.in_(user_habit_ids),
                    Occurrence.scheduled_local >= now_utc,
                    Occurrence.scheduled_local <= horizon,
                    Occurrence.outcome.is_(None)
                )
                .order_by(Occurrence.scheduled_local)
            )
            occurrences = list(occ_result.scalars().all())
            if not occurrences:
                continue

            # 2. Fetch user's calendar blocks
            cal_result = await db.execute(
                select(CalendarBlock)
                .where(
                    CalendarBlock.user_id == user.id,
                    CalendarBlock.end_time >= now_utc,
                    CalendarBlock.start_time <= horizon
                )
            )
            blocks = list(cal_result.scalars().all())

            # 3. Detect Conflicts
            # We assume a nominal duration of 15 minutes for each occurrence for intersection logic
            NOMINAL_DURATION = timedelta(minutes=15)

            for occ in occurrences:
                occ_start = occ.scheduled_local
                occ_end = occ_start + NOMINAL_DURATION
                
                # Check for existing alert for this occurrence
                existing_alert_result = await db.execute(
                    select(ConflictAlert).where(ConflictAlert.occurrence_id == occ.id)
                )
                if existing_alert_result.scalar_one_or_none():
                    continue  # Already flagged

                # Hard Conflict: Calendar Overlap
                overlap = False
                for b in blocks:
                    # Check intersection
                    if max(occ_start, b.start_time) < min(occ_end, b.end_time):
                        overlap = True
                        break
                
                if overlap:
                    alert = ConflictAlert(
                        user_id=user.id,
                        occurrence_id=occ.id,
                        conflict_type="hard_calendar",
                        description=f"Your habit is scheduled during a busy calendar block.",
                        detected_for_date=occ_start.date()
                    )
                    db.add(alert)
                    detected_hard += 1
                    continue

                # Hard Conflict: Occurrence Overlap
                for other_occ in occurrences:
                    if other_occ.id == occ.id:
                        continue
                    if other_occ.scheduled_local == occ_start:
                        alert = ConflictAlert(
                            user_id=user.id,
                            occurrence_id=occ.id,
                            conflict_type="hard_overlap",
                            description="Two habits are scheduled at the exact same time.",
                            detected_for_date=occ_start.date()
                        )
                        db.add(alert)
                        detected_hard += 1
                        overlap = True
                        break
                
                if overlap:
                    continue

                # Soft Conflict: Density (3+ occurrences in 30 mins)
                # Count occurrences within [occ_start - 15m, occ_start + 15m]
                window_start = occ_start - timedelta(minutes=15)
                window_end = occ_start + timedelta(minutes=15)
                dense_group = [
                    o for o in occurrences
                    if window_start <= o.scheduled_local <= window_end
                ]
                if len(dense_group) >= 3:
                    alert = ConflictAlert(
                        user_id=user.id,
                        occurrence_id=occ.id,
                        conflict_type="soft_density",
                        description="Your schedule is dense: 3+ habits within 30 minutes.",
                        detected_for_date=occ_start.date()
                    )
                    db.add(alert)
                    detected_soft += 1

        await db.commit()

    return {"detected_hard": detected_hard, "detected_soft": detected_soft}
