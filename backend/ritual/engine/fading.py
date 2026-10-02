"""Reminder fading, probe days, and unprompted-completion attribution.

Implements SPEC-habit-engine-v1 §5 and §6.

The design goal (PRD §4.3.5): a habit that only fires on notification is not a
habit, it is compliance with our notification. Fading is therefore the planned
end state, and we say so at the permission prompt.

Probe days are the measurement instrument (§5.3). Without deliberately
withholding a prompt we cannot distinguish "completed because we reminded them"
from "would have completed anyway" — and that distinction is the primary
success metric. Because a probe is deliberately withholding help, it is fenced
five ways, all enforced in :func:`assign_prompt_policies`.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from .models import (
    LAPSED_STATES,
    FadeLevel,
    Habit,
    HabitState,
    Occurrence,
    Outcome,
    PromptPolicy,
)

#: Consecutive unprompted completions required to fade one level (§5.2).
ADVANCE_STREAK = 3

#: A habit's first week is never probed (§5.3 fence 2).
PROBE_MIN_HABIT_AGE = timedelta(days=7)

#: Fence 3.
MAX_PROBES_PER_HABIT_PER_WEEK = 1
MAX_PROBES_PER_USER_PER_WEEK = 2


# --------------------------------------------------------------------------
# Which occurrences carry a prompt
# --------------------------------------------------------------------------


def _prompt_indices(count: int, n_prompts: int) -> set[int]:
    """Spread ``n_prompts`` prompts evenly across ``count`` occurrences.

    Even spacing rather than random selection: at L2 a user gets prompted on a
    predictable rhythm, which is kinder than an unpredictable one and easier to
    reason about when something looks wrong.
    """
    if n_prompts >= count:
        return set(range(count))
    if n_prompts <= 0:
        return set()
    return {round(i * count / n_prompts) for i in range(n_prompts)}


def prompts_restored(habit: Habit, at: datetime) -> bool:
    """True while a `forgot`-class coping plan has temporarily restored L0.

    Time-boxed to 7 days (§5.1) so that fading does not unravel through the
    coping-plan door — the one sanctioned way back up the ladder.
    """
    return habit.prompt_restore_until is not None and at < habit.prompt_restore_until


def effective_fade_level(habit: Habit, at: datetime) -> FadeLevel:
    if prompts_restored(habit, at):
        return FadeLevel.L0
    return habit.fade_level


def assign_prompt_policies(
    habit: Habit,
    week: Sequence[Occurrence],
    *,
    now: datetime,
    habit_created_at: datetime,
    user_probes_this_week: int = 0,
    last_probe_weekday: Optional[int] = None,
    rng: Optional[random.Random] = None,
) -> list[Occurrence]:
    """Assign PROMPT / SUPPRESS / PROBE across one week of occurrences.

    Called by the nightly materialiser so probe days are *planned* (§4.1).

    All five probe fences are enforced here rather than at fire time, because a
    fence checked at fire time is a fence that gets skipped under a deadline.
    """
    rng = rng or random.Random()
    level = effective_fade_level(habit, now)
    prompt_at = _prompt_indices(len(week), level.prompts_per_week)

    for i, occ in enumerate(week):
        occ.prompt_policy = (
            PromptPolicy.PROMPT if i in prompt_at else PromptPolicy.SUPPRESS
        )

    # --- Probe eligibility --------------------------------------------------
    # Fence 1: never while lapsed, dormant, paused, graduated or retired.
    if habit.state is not HabitState.FORMING and habit.state is not HabitState.ESTABLISHED:
        return list(week)
    # Fence 2: never in the habit's first week.
    if now - habit_created_at < PROBE_MIN_HABIT_AGE:
        return list(week)
    # Fence 3: per-user weekly cap.
    if user_probes_this_week >= MAX_PROBES_PER_USER_PER_WEEK:
        return list(week)
    # A habit already at L4 has no prompt to withhold.
    if level is FadeLevel.L4:
        return list(week)

    candidates = [
        i
        for i in sorted(prompt_at)
        # Fence 4: never the same weekday slot two consecutive weeks.
        if week[i].scheduled_local.weekday() != last_probe_weekday
    ]
    if not candidates:
        return list(week)

    week[rng.choice(candidates)].prompt_policy = PromptPolicy.PROBE
    return list(week)


# --------------------------------------------------------------------------
# Attribution
# --------------------------------------------------------------------------


def unprompted_at(
    completed_at: Optional[datetime], prompt_delivered_at: Optional[datetime]
) -> bool:
    """The attribution rule, over bare timestamps.

    Exists so the persistence layer can apply it without constructing an
    Occurrence. Note what it does *not* take: send time. A prompt that was sent
    but not delivered did not reach the user, so it cannot have caused
    anything, and falling back to send time in its absence silently converts
    every undelivered prompt into a prompted completion.
    """
    if completed_at is None:
        return False
    if prompt_delivered_at is None:
        return True
    return completed_at < prompt_delivered_at


def is_unprompted(occ: Occurrence) -> bool:
    """SPEC-habit-engine §6.1.

    Delivery time governs, not send time. A prompt sent at 07:00 and delivered
    at 09:40 when the phone came off airplane mode did not cause an 08:15
    completion — and treating it as prompted would understate automaticity for
    exactly the users whose phones are least reliable.
    """
    return unprompted_at(occ.completed_at, occ.prompt_delivered_at)


def resolve_outcome(occ: Occurrence) -> Outcome:
    """Final outcome for a closed occurrence.

    A miss on a probe day is a ``PROBE_MISS``: we withheld the prompt, so we
    absorb the consequence. It is excluded from lapse progression and streak
    loss (§5.3, final rule).
    """
    if occ.outcome in (Outcome.SKIPPED, Outcome.REST):
        return occ.outcome
    if occ.completed_at is not None:
        return Outcome.COMPLETED
    if occ.prompt_policy is PromptPolicy.PROBE:
        return Outcome.PROBE_MISS
    return Outcome.MISSED


def counts_toward_lapse(outcome: Outcome) -> bool:
    """Only a genuine miss advances lapse state."""
    return outcome is Outcome.MISSED


# --------------------------------------------------------------------------
# Ladder movement
# --------------------------------------------------------------------------


def should_advance(habit: Habit, recent: Sequence[Occurrence]) -> bool:
    """Advance after ADVANCE_STREAK consecutive unprompted completions (§5.2).

    ``recent`` is most-recent-first. Skips and rest days are transparent: they
    neither break nor extend the streak, because a user who told us they were
    not doing it has not failed at automaticity.
    """
    if habit.state in LAPSED_STATES or habit.state is HabitState.PAUSED:
        return False
    if habit.fade_level is FadeLevel.L4:
        return False

    streak = 0
    for occ in recent:
        outcome = resolve_outcome(occ)
        if outcome in (Outcome.SKIPPED, Outcome.REST):
            continue
        if outcome is Outcome.COMPLETED and is_unprompted(occ):
            streak += 1
            if streak >= ADVANCE_STREAK:
                return True
            continue
        return False
    return False


def advance(level: FadeLevel) -> FadeLevel:
    return FadeLevel(min(int(level) + 1, int(FadeLevel.L4)))


def regress(level: FadeLevel) -> FadeLevel:
    """One level, never to L0 (§5.2).

    Regression is a support adjustment, not a penalty. Dropping someone to daily
    prompts after a bad week reads as one.
    """
    return FadeLevel(max(int(level) - 1, int(FadeLevel.L1)))


def unprompted_rate(occurrences: Iterable[Occurrence]) -> Optional[float]:
    """Unprompted completions over probe-eligible occurrences.

    Restricting the denominator matters when comparing across fade levels
    (§6.2): measured over *all* occurrences the metric rises trivially with
    fading and tells us nothing about automaticity.
    """
    eligible = [
        o
        for o in occurrences
        if o.prompt_policy in (PromptPolicy.PROMPT, PromptPolicy.PROBE)
        and resolve_outcome(o) in (Outcome.COMPLETED, Outcome.MISSED, Outcome.PROBE_MISS)
    ]
    if not eligible:
        return None
    return sum(1 for o in eligible if is_unprompted(o)) / len(eligible)
