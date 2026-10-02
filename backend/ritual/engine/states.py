"""Habit state transitions and recovery surfacing.

Implements SPEC-habit-engine-v1 §2.1 and SPEC-failure-layer-v1 §2–§3.

The rule that governs this module, from D1:

    We never raise the first miss. We always answer it if the user does.

After one miss most people have not registered a failure. Surfacing it *tells
them one occurred* — manufacturing the exact event the failure layer exists to
soften. So `lapsed_1` remains a tracked state (it drives skip-annotation
capture, coping-plan seeding and the recovery metric) but has no push-side
trigger at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Sequence

from .models import HabitState, Occurrence, Outcome

#: SPEC-failure-layer §1: a completion within this window of a miss counts as a
#: recovery. D3 kept it as a *metric definition only* — nothing the user
#: experiences depends on it. It spans a weekend, which is the shape of most
#: real lapses.
RECOVERY_WINDOW = timedelta(hours=72)

#: Misses to reach each depth.
LAPSED_2_AT = 2
DORMANT_AT = 4
DORMANT_IDLE = timedelta(days=10)
RETIRE_AFTER_DORMANT = timedelta(days=21)

#: §9.1 bad week: suppress every individual recovery break and offer one
#: whole-account message instead.
BAD_WEEK_MISSES = 5
BAD_WEEK_WINDOW = timedelta(hours=48)

#: §3.1 delivery caps.
MAX_BREAKS_PER_HABIT = timedelta(hours=72)
MAX_BREAKS_PER_USER_PER_DAY = 2


class Trigger(str, Enum):
    """How we arrived at a potential recovery surface."""

    #: The system noticed. Subject to D1: silent at one miss.
    PUSH = "push"
    #: The user opened the app of their own accord. A pull gets answered.
    PULL = "pull"


class RecoverySurface(str, Enum):
    NONE = "none"
    #: Inline on the habit card. One miss, pull only. Not a modal, not a push.
    LIGHT_ACK = "light_ack"
    #: The four-step 45-second break.
    FULL_BREAK = "full_break"
    DORMANT_RETURN = "dormant_return"
    #: One whole-account message; individual breaks suppressed.
    BAD_WEEK = "bad_week"


@dataclass
class LapseCounters:
    """Per-habit lapse bookkeeping."""

    consecutive_misses: int = 0
    last_miss_at: Optional[datetime] = None
    entered_dormant_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None
    last_break_at: Optional[datetime] = None
    #: D5: quick-setup users are offered WOOP at first lapse, once.
    woop_offers_declined: int = 0


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


def _lapse_depth(consecutive_misses: int) -> HabitState:
    if consecutive_misses >= DORMANT_AT:
        return HabitState.DORMANT
    if consecutive_misses >= LAPSED_2_AT:
        return HabitState.LAPSED_2
    if consecutive_misses >= 1:
        return HabitState.LAPSED_1
    return HabitState.FORMING


def apply_outcome(
    state: HabitState,
    counters: LapseCounters,
    outcome: Outcome,
    at: datetime,
) -> tuple[HabitState, LapseCounters, list[str]]:
    """Advance state for one closed occurrence.

    Returns ``(new_state, counters, events)``. Events are emitted rather than
    written so the caller owns persistence and analytics.

    ``paused``, ``graduated`` and ``retired`` are inert here: every lapse rule
    checks them first. A user in transition mode who receives a lapse message
    has been failed by us, not the other way around.
    """
    events: list[str] = []

    if state in (HabitState.PAUSED, HabitState.GRADUATED, HabitState.RETIRED):
        return state, counters, events

    # Skips, rest days and probe misses never advance lapse depth. A probe miss
    # was caused by us withholding the prompt, so we absorb it (§5.3).
    if outcome in (Outcome.SKIPPED, Outcome.REST, Outcome.PROBE_MISS):
        counters.last_interaction_at = at
        return state, counters, events

    if outcome is Outcome.COMPLETED:
        counters.last_interaction_at = at
        if counters.last_miss_at is not None:
            if at - counters.last_miss_at <= RECOVERY_WINDOW:
                events.append(
                    "recovered_deep" if state is HabitState.LAPSED_2 else "recovered"
                )
        counters.consecutive_misses = 0
        counters.last_miss_at = None
        counters.entered_dormant_at = None
        new_state = (
            HabitState.FORMING if state is not HabitState.ESTABLISHED else state
        )
        return new_state, counters, events

    if outcome is Outcome.MISSED:
        counters.consecutive_misses += 1
        counters.last_miss_at = at
        new_state = _lapse_depth(counters.consecutive_misses)
        if new_state is HabitState.DORMANT and state is not HabitState.DORMANT:
            counters.entered_dormant_at = at
        if new_state is not state:
            events.append(f"entered_{new_state.value}")
        return new_state, counters, events

    return state, counters, events


def check_idle(
    state: HabitState, counters: LapseCounters, now: datetime
) -> tuple[HabitState, list[str]]:
    """Dormancy from inactivity, and eligibility for retirement.

    Retirement is *offered*, never applied: a habit disappearing on its own is
    indistinguishable from a bug, and it takes the decision away from the person
    whose habit it is.
    """
    events: list[str] = []
    if state in (HabitState.PAUSED, HabitState.GRADUATED, HabitState.RETIRED):
        return state, events

    last = counters.last_interaction_at
    if last is not None and now - last >= DORMANT_IDLE and state is not HabitState.DORMANT:
        counters.entered_dormant_at = now
        events.append("entered_dormant")
        return HabitState.DORMANT, events

    if (
        state is HabitState.DORMANT
        and counters.entered_dormant_at is not None
        and now - counters.entered_dormant_at >= RETIRE_AFTER_DORMANT
    ):
        # Offer only. The caller must obtain confirmation before retiring.
        events.append("retirement_offer_due")

    return state, events


# ---------------------------------------------------------------------------
# Bad week
# ---------------------------------------------------------------------------


def is_bad_week(misses: Sequence[datetime], now: datetime) -> bool:
    """Five or more misses across all habits inside 48 hours (§9.1).

    The highest-value single screen in the failure layer: it is the moment users
    delete the app, and every competitor responds to it with six notifications.
    """
    recent = [m for m in misses if now - m <= BAD_WEEK_WINDOW]
    return len(recent) >= BAD_WEEK_MISSES


# ---------------------------------------------------------------------------
# What to show
# ---------------------------------------------------------------------------


def recovery_surface(
    state: HabitState,
    trigger: Trigger,
    *,
    now: datetime,
    counters: LapseCounters,
    bad_week: bool = False,
    breaks_shown_today: int = 0,
    dismissals: int = 0,
) -> RecoverySurface:
    """Decide the recovery surface for one habit.

    Order of checks matters and is deliberate:

    1. Inert states first — nothing surfaces for paused/graduated/retired.
    2. Bad week overrides everything else, and suppresses per-habit breaks.
    3. D1: one miss is silent on push, a light acknowledgment on pull.
    4. Caps last, so a user having a hard week is not buried.
    """
    if state in (HabitState.PAUSED, HabitState.GRADUATED, HabitState.RETIRED):
        return RecoverySurface.NONE

    if bad_week:
        return RecoverySurface.BAD_WEEK

    if state is HabitState.FORMING or state is HabitState.ESTABLISHED:
        return RecoverySurface.NONE

    # Three dismissals suppress this habit's breaks for 14 days (§3.1). Someone
    # who has closed it three times has told us something.
    if dismissals >= 3:
        return RecoverySurface.NONE

    if state is HabitState.LAPSED_1:
        # D1. The whole rule, in two lines.
        return (
            RecoverySurface.LIGHT_ACK
            if trigger is Trigger.PULL
            else RecoverySurface.NONE
        )

    if breaks_shown_today >= MAX_BREAKS_PER_USER_PER_DAY:
        return RecoverySurface.NONE
    if (
        counters.last_break_at is not None
        and now - counters.last_break_at < MAX_BREAKS_PER_HABIT
    ):
        return RecoverySurface.NONE

    if state is HabitState.DORMANT:
        return RecoverySurface.DORMANT_RETURN

    return RecoverySurface.FULL_BREAK


def should_offer_woop(
    plan_type: str, state: HabitState, trigger: Trigger, counters: LapseCounters
) -> bool:
    """D5: offer WOOP to quick-setup users at their first lapse.

    On day one the obstacle question is hypothetical and users guess. After a
    real miss they know, and the drill-down writes itself.

    Offered on the pull-side light acknowledgment only, and never again after
    two declines.
    """
    return (
        plan_type == "if_then"
        and state is HabitState.LAPSED_1
        and trigger is Trigger.PULL
        and counters.woop_offers_declined < 2
    )


def lapse_recovery_rate(
    misses: Sequence[tuple[datetime, Optional[datetime]]]
) -> Optional[float]:
    """The headline metric (PRD §9.2).

    ``misses`` is a sequence of ``(miss_at, recovered_at_or_None)``.

    If this does not move, the failure layer is theatre — which is why it ships
    first and why a holdout must exist before launch.
    """
    if not misses:
        return None
    recovered = sum(
        1
        for miss_at, rec_at in misses
        if rec_at is not None and rec_at - miss_at <= RECOVERY_WINDOW
    )
    return recovered / len(misses)
