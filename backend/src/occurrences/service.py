"""
Occurrences service — completion, skip, and unprompted attribution.

Unprompted attribution (Habit Engine §6.1):
  "Delivery time rather than send time is the whole subtlety here.
   A prompt sent at 07:00 and delivered at 09:40 when the phone came
   off airplane mode did not cause an 08:15 completion."
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ritual.engine.fading import unprompted_at
from src.occurrences.models import Occurrence


def compute_unprompted(
    prompt_sent_at: datetime | None,
    prompt_delivered_at: datetime | None,
    completed_at: datetime,
) -> bool:
    """
    Determine whether a completion was unprompted.

    Rules (Habit Engine §6.1):
    - No prompt sent (probe or suppressed) → unprompted = True
    - Prompt sent but not delivered → unprompted = True
    - Completion before delivery time → unprompted = True
    - Completion after delivery → unprompted = False

    Uses DELIVERY time, not send time. `prompt_sent_at` is accepted for call
    compatibility and deliberately unused: an earlier version fell back to it
    when delivery was unknown (`prompt_delivered_at or prompt_sent_at`), which
    inverted the rule the docstring states. A prompt sent at 07:00 and never
    delivered, completed at 08:15, was scored as *prompted* — the precise case
    §6.1 exists to get right, and one that would have understated automaticity
    for users with the least reliable phones.

    Delegates to the domain core so the rule has one implementation.
    """
    del prompt_sent_at  # see above: delivery governs, send time never does
    return unprompted_at(completed_at, prompt_delivered_at)


async def complete_occurrence(
    db: AsyncSession,
    occurrence: Occurrence,
    completion_source: str,
    prompt_delivered_at: datetime | None = None,
) -> Occurrence:
    now = datetime.now(timezone.utc)
    occurrence.completed_at = now
    occurrence.completion_source = completion_source
    occurrence.outcome = "completed"
    # Persist delivery time before deriving from it, and prefer an already
    # recorded delivery over one supplied by this call: the dispatcher knows
    # when the push actually landed, a completion request only claims to.
    if prompt_delivered_at is not None and occurrence.prompt_delivered_at is None:
        occurrence.prompt_delivered_at = prompt_delivered_at
    occurrence.unprompted = compute_unprompted(
        occurrence.prompt_sent_at,
        occurrence.prompt_delivered_at,
        now,
    )
    await db.flush()
    return occurrence


async def skip_occurrence(
    db: AsyncSession,
    occurrence: Occurrence,
    annotation: str | None = None,
) -> Occurrence:
    """
    Mark as skipped (user-initiated before/during window).
    Skip is a first-class action — §1.1 of SPEC-failure-layer:
    "A user who taps 'not today' has done something good."
    """
    occurrence.outcome = "skipped"
    occurrence.skip_annotation = annotation
    await db.flush()
    return occurrence


async def get_occurrence(
    db: AsyncSession, occurrence_id: uuid.UUID
) -> Occurrence | None:
    result = await db.execute(
        select(Occurrence).where(Occurrence.id == occurrence_id)
    )
    return result.scalar_one_or_none()
