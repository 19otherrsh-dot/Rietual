"""Habit graduation.

Implements SPEC-habit-engine-v1 §9, which exists because of D10:

    Ship graduation. Habits leave tracking at sustained SRBAI, reminders stop,
    and we say so in marketing. Not negotiable — the alternative is a product
    with a structural interest in the user never succeeding.

Three criteria, all simultaneously (§9.1):

  1. SRBAI at or above threshold on **two consecutive** biweekly measures
  2. Fade level L4 — no scheduled prompts
  3. >= 80% completion over the trailing 30 days, **on probe-eligible
     occurrences only**

Criterion 3's denominator matters. Measured over all occurrences it rises
trivially once prompts stop, which would let a habit graduate on the strength
of us having stopped asking. Restricting to occurrences we would have prompted
(or deliberately did not, on a probe day) keeps it a statement about the user
rather than about our notification schedule.

Graduation is a *one-way door for prompting*: re-entry is offered at the
maintenance check and never forced, and prompts are never re-enabled without
consent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from .fading import resolve_outcome
from .models import FadeLevel, HabitState, Occurrence, Outcome, PromptPolicy

#: SRBAI mean at or above this counts as a passing measure. Conservative;
#: validate against our own cohort at 6 months (§10 open question 1).
SRBAI_THRESHOLD = 5.5

#: Consecutive passing measures required.
REQUIRED_CONSECUTIVE_MEASURES = 2

#: Cadence of SRBAI measurement per habit.
MEASURE_INTERVAL = timedelta(days=14)

#: Trailing completion window and floor.
COMPLETION_WINDOW = timedelta(days=30)
COMPLETION_FLOOR = 0.80

#: Maintenance checks after graduation. One question, once, no nagging.
MAINTENANCE_CHECKS = (timedelta(days=30), timedelta(days=90))


@dataclass(frozen=True)
class SRBAIMeasure:
    measured_at: datetime
    mean_score: float

    @property
    def passing(self) -> bool:
        return self.mean_score >= SRBAI_THRESHOLD


@dataclass(frozen=True)
class GraduationCheck:
    """Why a habit did or did not graduate.

    Every criterion is reported, not just the failing one: this feeds the
    progress surface that tells a user what is left, and "not yet, here is
    what remains" is a far better message than a silent no.
    """

    eligible: bool
    srbai_met: bool
    fade_met: bool
    completion_met: bool
    consecutive_passing: int = 0
    completion_rate: Optional[float] = None
    eligible_occurrences: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)


def consecutive_passing_measures(measures: Sequence[SRBAIMeasure]) -> int:
    """Count passing measures from the most recent backwards.

    ``measures`` may be in any order; it is sorted by time here so callers
    cannot get this subtly wrong by passing a database result set whose
    ordering they did not specify.
    """
    ordered = sorted(measures, key=lambda m: m.measured_at, reverse=True)
    streak = 0
    for m in ordered:
        if not m.passing:
            break
        streak += 1
    return streak


def probe_eligible(occurrence: Occurrence) -> bool:
    """Occurrences that would have carried a prompt, or deliberately did not.

    Suppressed occurrences are excluded: at L3 a habit has six unprompted days
    a week that say nothing about automaticity, and counting them would let
    fading alone carry a habit over the line.
    """
    return occurrence.prompt_policy in (PromptPolicy.PROMPT, PromptPolicy.PROBE)


def trailing_completion_rate(
    occurrences: Iterable[Occurrence], *, now: datetime
) -> tuple[Optional[float], int]:
    """(rate, n) over probe-eligible occurrences in the trailing 30 days.

    Skips and rest days are excluded from both numerator and denominator — a
    user who told us they were not doing it has not failed at anything, and
    counting it against them here would penalise exactly the honest logging
    the skip action exists to encourage.
    """
    cutoff = now - COMPLETION_WINDOW
    considered: list[Occurrence] = []
    for occ in occurrences:
        if occ.scheduled_local < cutoff or occ.scheduled_local > now:
            continue
        if not probe_eligible(occ):
            continue
        outcome = resolve_outcome(occ)
        if outcome in (Outcome.SKIPPED, Outcome.REST, Outcome.PENDING):
            continue
        considered.append(occ)

    if not considered:
        return None, 0

    completed = sum(
        1 for o in considered if resolve_outcome(o) is Outcome.COMPLETED
    )
    return completed / len(considered), len(considered)


def check_graduation(
    *,
    state: HabitState,
    fade_level: FadeLevel,
    measures: Sequence[SRBAIMeasure],
    occurrences: Iterable[Occurrence],
    now: datetime,
) -> GraduationCheck:
    """Evaluate all three criteria. Pure; the caller applies the transition.

    Takes `state` and `fade_level` rather than a `Habit` because the
    application layer stores habits as ORM rows, not as this package's
    dataclass. Asking for the two fields the rule actually reads keeps the core
    usable from both sides without an adapter that exists only to satisfy a
    type.
    """
    reasons: list[str] = []

    streak = consecutive_passing_measures(measures)
    srbai_met = streak >= REQUIRED_CONSECUTIVE_MEASURES
    if not srbai_met:
        reasons.append(
            f"{streak} of {REQUIRED_CONSECUTIVE_MEASURES} consecutive SRBAI "
            f"measures at or above {SRBAI_THRESHOLD}"
        )

    fade_met = fade_level is FadeLevel.L4
    if not fade_met:
        reasons.append(f"still prompted at L{int(fade_level)}")

    rate, n = trailing_completion_rate(occurrences, now=now)
    completion_met = rate is not None and rate >= COMPLETION_FLOOR
    if rate is None:
        reasons.append("no probe-eligible occurrences in the last 30 days")
    elif not completion_met:
        reasons.append(f"{rate:.0%} completion over 30 days, needs {COMPLETION_FLOOR:.0%}")

    # A habit that is lapsed, paused or already graduated is not a candidate,
    # regardless of what its history says.
    state_ok = state in (HabitState.FORMING, HabitState.ESTABLISHED)
    if not state_ok:
        reasons.append(f"state is {state.value}")

    return GraduationCheck(
        eligible=srbai_met and fade_met and completion_met and state_ok,
        srbai_met=srbai_met,
        fade_met=fade_met,
        completion_met=completion_met,
        consecutive_passing=streak,
        completion_rate=rate,
        eligible_occurrences=n,
        reasons=tuple(reasons),
    )


def next_measure_due(
    last_measured_at: Optional[datetime], *, created_at: datetime
) -> datetime:
    """When this habit's next SRBAI measure is due (biweekly)."""
    return (last_measured_at or created_at) + MEASURE_INTERVAL


def maintenance_check_dates(graduated_at: datetime) -> tuple[datetime, ...]:
    """Day 30 and day 90 after graduation. One question, once, no nagging."""
    return tuple(graduated_at + offset for offset in MAINTENANCE_CHECKS)


def graduation_message(*, weeks: int, unprompted_days: int) -> str:
    """The graduation moment (§9.3).

    Deliberately not a quiet state change. This is the strongest positive
    moment the product has, and we are the only product with an incentive to
    say it — so saying it well is most of the value of D10.

    Note what it does *not* contain: no streak count, no percentage, no score,
    no upsell, and no suggestion of what to start next. That belongs to a
    later screen, not to this one.
    """
    return (
        f"This one's yours now.\n\n"
        f"{weeks} weeks. The last {unprompted_days} days you did it without a "
        f"single reminder from us — that's the definition we use, and you've "
        f"met it. We'll stop bringing it up."
    )
