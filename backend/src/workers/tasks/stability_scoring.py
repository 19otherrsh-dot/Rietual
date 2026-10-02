"""Anchor stability scoring task — recomputes nightly using circular statistics."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from src.workers.celery_app import celery_app


@celery_app.task(name="src.workers.tasks.stability_scoring.score_anchor_stability")
def score_anchor_stability() -> dict:
    return asyncio.run(_async_score())


async def _async_score() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.habits.models import Anchor
    from src.habits.stability import (
        overall_level,
        score_calendar,
        score_locational,
        score_temporal,
    )
    from src.occurrences.models import Occurrence

    scored = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    async with AsyncSessionLocal() as db:
        anchors_result = await db.execute(select(Anchor))
        anchors = list(anchors_result.scalars().all())

        for anchor in anchors:
            # Fetch recent completed occurrences for habits on this anchor
            from src.habits.models import Habit
            habits_result = await db.execute(
                select(Habit.id).where(Habit.anchor_id == anchor.id)
            )
            habit_ids = [r for r in habits_result.scalars()]

            if not habit_ids:
                continue

            occ_result = await db.execute(
                select(Occurrence)
                .where(
                    Occurrence.habit_id.in_(habit_ids),
                    Occurrence.outcome == "completed",
                    Occurrence.completed_at >= cutoff,
                )
                .order_by(Occurrence.completed_at)
            )
            occs = list(occ_result.scalars().all())

            if len(occs) < 5:
                anchor.stability = "unscored"
                anchor.stability_basis = "prior"
                continue

            # Extract times of day from wall-clock completions
            from zoneinfo import ZoneInfo

            from src.users.models import User
            user_result = await db.execute(
                select(User).where(User.id == anchor.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                continue

            try:
                tz = ZoneInfo(user.timezone)
            except Exception:
                tz = ZoneInfo("UTC")

            local_times = [
                o.completed_at.astimezone(tz).time()
                for o in occs
                if o.completed_at is not None
            ]

            temporal = score_temporal(local_times)

            # Locational and calendar scores: computed from client-sent metrics
            # stored on the Anchor row directly
            locational = None
            if anchor.locational_cluster_share is not None:
                locational = score_locational(anchor.locational_cluster_share, len(occs))

            calendar = None
            if anchor.calendar_shape_share is not None:
                calendar = score_calendar(anchor.calendar_shape_share, len(occs))

            anchor.stability = overall_level(temporal, locational, calendar)
            anchor.stability_basis = temporal.basis
            anchor.temporal_mad_minutes = temporal.value
            scored += 1

        await db.commit()

    return {"scored": scored}
