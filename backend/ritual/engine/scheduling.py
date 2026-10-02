"""Occurrence generation in local wall clock.

Implements SPEC-habit-engine-v1 §4.

The governing rule (§4.2): `scheduled_local` is a local wall-clock time plus a
timezone identifier. A 07:00 habit is at 07:00 through a DST transition, and it
is at 07:00 local after the user flies to Lisbon.

Three failure modes this exists to prevent, all routine in this category:

* storing UTC and shifting everyone's morning routine by an hour twice a year
* generating a duplicate or missing occurrence on the transition day
* prompting someone at 4am on their first morning abroad
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

from .models import (
    Anchor,
    Habit,
    Occurrence,
    PromptPolicy,
    Stability,
    StabilityReport,
)

#: Quiet hours. No miss detection and no prompt fires inside this window.
#: SPEC-failure-layer §1.2 — "someone who does their evening routine at 21:40
#: instead of 21:00 has not failed at anything".
QUIET_START = time(22, 0)
QUIET_END = time(7, 0)

#: Grace after the window closes before a miss is recorded.
MISS_GRACE = timedelta(hours=2)

#: SPEC-habit-engine §4.4. A wider window on an unstable anchor is not leniency,
#: it is an accurate model of when the cue actually occurs.
WINDOW_STABLE = timedelta(minutes=90)
WINDOW_UNSTABLE = timedelta(hours=3)


class NonexistentLocalTime(ValueError):
    """Raised only when a caller explicitly asks for strict resolution."""


def resolve_local(naive: datetime, tz: ZoneInfo, *, strict: bool = False) -> datetime:
    """Attach ``tz`` to a naive local wall-clock time, resolving DST edges.

    Two edge cases, both of which occur twice a year in most zones:

    * **Nonexistent** (spring forward): the wall time falls in the gap. We shift
      forward by the size of the gap, so an 02:30 habit fires at 03:30 on that
      one day rather than being silently dropped.
    * **Ambiguous** (fall back): the wall time happens twice. We take the first
      instant (``fold=0``), deterministically, so the habit does not fire twice.

    Both choices are arbitrary but must be *stable*; the failure we care about
    is a duplicated or vanished occurrence, not which side of an hour it lands.
    """
    aware = naive.replace(tzinfo=tz)
    off0 = aware.replace(fold=0).utcoffset()
    off1 = aware.replace(fold=1).utcoffset()

    if off0 == off1:
        return aware  # ordinary case, no transition nearby

    # Distinguish gap from fold: a gap time does not survive a round trip
    # through UTC, an ambiguous one does.
    round_tripped = aware.astimezone(timezone.utc).astimezone(tz)
    if round_tripped.replace(tzinfo=None, fold=0) != naive.replace(fold=0):
        if strict:
            raise NonexistentLocalTime(f"{naive} does not exist in {tz}")
        gap = off1 - off0
        return (naive + gap).replace(tzinfo=tz)

    return aware.replace(fold=0)


def window_for(stability: Optional[StabilityReport]) -> timedelta:
    """Half-width of the completion window for an anchor's stability."""
    if stability is None or stability.verdict in (Stability.UNKNOWN, Stability.STABLE):
        return WINDOW_STABLE
    return WINDOW_UNSTABLE


def _parse_nominal(nominal_time: str) -> time:
    hh, mm = nominal_time.split(":")
    return time(int(hh), int(mm))


def generate_occurrences(
    habit: Habit,
    anchor: Anchor,
    start: date,
    days: int = 7,
    *,
    weekdays: Optional[Sequence[int]] = None,
    id_prefix: str = "occ",
) -> list[Occurrence]:
    """Materialise ``days`` of occurrences from ``start`` inclusive.

    Materialised ahead (§4.1) so that prompt policy and probe days can be
    *planned* rather than decided at fire time.

    ``weekdays`` filters by ``date.weekday()`` (0 = Monday) for habits that do
    not run daily; ``None`` means every day.
    """
    if anchor.nominal_time is None:
        raise ValueError(
            f"anchor {anchor.id} has no nominal_time; event anchors are not "
            "schedulable without an observed time"
        )

    tz = ZoneInfo(habit.timezone)
    nominal = _parse_nominal(anchor.nominal_time)
    half = window_for(anchor.stability)

    out: list[Occurrence] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        if weekdays is not None and day.weekday() not in weekdays:
            continue

        scheduled = resolve_local(datetime.combine(day, nominal), tz)
        out.append(
            Occurrence(
                id=f"{id_prefix}-{habit.id}-{day.isoformat()}",
                habit_id=habit.id,
                scheduled_local=scheduled,
                window_start=scheduled - half,
                window_end=scheduled + half,
                prompt_policy=PromptPolicy.PROMPT,
            )
        )
    return out


def is_quiet_hours(moment: datetime) -> bool:
    """True inside the 22:00–07:00 local no-contact window."""
    t = moment.timetz().replace(tzinfo=None)
    return t >= QUIET_START or t < QUIET_END


def miss_detection_due_at(occurrence: Occurrence) -> datetime:
    """When a miss on this occurrence may first be *recorded*.

    Window close plus grace, deferred out of quiet hours. Deferring matters:
    detecting a miss at 23:30 and surfacing it at 23:31 is how a product earns
    its uninstall, and the failure layer's own delivery rules assume detection
    never lands overnight.
    """
    due = occurrence.window_end + MISS_GRACE
    if not is_quiet_hours(due):
        return due

    # Defer to 07:00 — today's if we are in the pre-dawn tail, else tomorrow's.
    next_day = due.date() if due.timetz().replace(tzinfo=None) < QUIET_END else due.date() + timedelta(days=1)
    return resolve_local(datetime.combine(next_day, QUIET_END), due.tzinfo)


def detect_timezone_change(previous: str, current: str, at: datetime) -> Optional[timedelta]:
    """Return the UTC-offset delta if the user has moved zones, else None.

    A shift of >= 2 hours pauses stability scoring for 3 days after the zone
    settles (SPEC-habit-engine §4.3). Travel makes every anchor look unstable,
    and that is exactly the wrong moment to tell someone their life is too
    irregular.
    """
    if previous == current:
        return None
    naive = at.replace(tzinfo=None)
    before = naive.replace(tzinfo=ZoneInfo(previous)).utcoffset()
    after = naive.replace(tzinfo=ZoneInfo(current)).utcoffset()
    assert before is not None and after is not None
    return after - before


STABILITY_PAUSE_THRESHOLD = timedelta(hours=2)
STABILITY_PAUSE_DURATION = timedelta(days=3)


def stability_scoring_paused_until(
    delta: Optional[timedelta], settled_at: datetime
) -> Optional[datetime]:
    """When stability scoring may resume after a timezone change."""
    if delta is None or abs(delta) < STABILITY_PAUSE_THRESHOLD:
        return None
    return settled_at + STABILITY_PAUSE_DURATION
