"""Sleep Reset — window titration.

Implements SPEC-journeys-v1 §5.3–§5.4.

This is the only module in the codebase that can hurt someone if it is wrong.
Clinical sleep restriction sets time-in-bed to measured total sleep time, which
can mean an initial window of five hours and a genuinely rough first week —
under clinician supervision. We are not a clinician and the user is alone with
their phone, so this implements the gentler *compression* adaptation with three
safety properties that are invariants, not preferences:

1. **A hard floor of 5.5 hours.** The algorithm may never propose a window below
   it, regardless of what the diary says.
2. **Sleepiness overrides efficiency.** Daytime sleepiness is the known adverse
   effect of this protocol and the one that hurts people outside the app.
3. **Never titrate on imputed data.** A window computed from a guess is a real
   intervention derived from a fiction.

None of this ships without clinical sign-off (SPEC-journeys §8).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional, Sequence

#: Invariant 1. 5.5 hours.
FLOOR_MINUTES = 330

#: Start gentle: measured sleep plus half an hour, not measured sleep exactly.
INITIAL_BUFFER_MINUTES = 30

STEP_MINUTES = 15
SLEEPINESS_EXTENSION_MINUTES = 30

#: Titration reads the trailing five nights and needs at least four of them.
TRAILING_NIGHTS = 5
MIN_NIGHTS_FOR_TITRATION = 4

EXTEND_AT = 0.90
HOLD_AT = 0.85


class Action(str, Enum):
    EXTEND = "extend"
    HOLD = "hold"
    COMPRESS = "compress"
    #: Insufficient diary data. The window holds where it is (§5.4).
    PAUSED_MISSING_DATA = "paused_missing_data"
    #: Invariant 2 fired: sleepiness beat efficiency.
    SLEEPINESS_OVERRIDE = "sleepiness_override"
    #: Invariant 1 fired: compression was refused.
    FLOOR_REACHED = "floor_reached"


@dataclass(frozen=True)
class SleepNight:
    night_of: date
    time_in_bed_min: Optional[int] = None
    total_sleep_min: Optional[int] = None

    @property
    def is_complete(self) -> bool:
        return (
            self.time_in_bed_min is not None
            and self.total_sleep_min is not None
            and self.time_in_bed_min > 0
        )


@dataclass(frozen=True)
class TitrationResult:
    window_minutes: int
    action: Action
    sleep_efficiency: Optional[float]
    nights_used: int
    #: Plain-language reason, surfaced to the user. The protocol is handed to
    #: them at journey exit (§5.6), so it must always be explicable.
    reason: str


def sleep_efficiency(nights: Sequence[SleepNight]) -> Optional[float]:
    """Total sleep time over time in bed, across complete nights only."""
    complete = [n for n in nights if n.is_complete]
    if not complete:
        return None
    in_bed = sum(n.time_in_bed_min for n in complete)  # type: ignore[misc]
    asleep = sum(n.total_sleep_min for n in complete)  # type: ignore[misc]
    if in_bed <= 0:
        return None
    return asleep / in_bed


def initial_window(average_total_sleep_min: int) -> int:
    """Opening window for the journey.

    Measured sleep plus 30 minutes, never below the floor. A user reporting
    three hours of sleep a night gets 5.5 hours, not 3.5 — the diary may be
    wrong, the floor never is.
    """
    return max(FLOOR_MINUTES, average_total_sleep_min + INITIAL_BUFFER_MINUTES)


def titrate(
    current_window_min: int,
    nights: Sequence[SleepNight],
    *,
    severe_sleepiness: bool = False,
) -> TitrationResult:
    """One titration step.

    Order of checks encodes the safety priority: sleepiness first, then data
    sufficiency, then efficiency. Efficiency is the *least* important input,
    which is the opposite of how the clinical algorithm is usually written and
    is deliberate for an unsupervised setting.
    """
    trailing = list(nights)[-TRAILING_NIGHTS:]
    complete = [n for n in trailing if n.is_complete]
    efficiency = sleep_efficiency(trailing)

    # Invariant 2 — overrides everything, including missing data.
    if severe_sleepiness:
        return TitrationResult(
            window_minutes=current_window_min + SLEEPINESS_EXTENSION_MINUTES,
            action=Action.SLEEPINESS_OVERRIDE,
            sleep_efficiency=efficiency,
            nights_used=len(complete),
            reason=(
                "You reported feeling very sleepy during the day, so we have "
                "given you half an hour back. That comes before anything else."
            ),
        )

    # Invariant 3 — hold rather than impute.
    if len(complete) < MIN_NIGHTS_FOR_TITRATION:
        return TitrationResult(
            window_minutes=current_window_min,
            action=Action.PAUSED_MISSING_DATA,
            sleep_efficiency=efficiency,
            nights_used=len(complete),
            reason=(
                "Not enough diary entries this week, so your window stays where "
                "it is. We do not guess at this."
            ),
        )

    assert efficiency is not None

    if efficiency >= EXTEND_AT:
        return TitrationResult(
            window_minutes=current_window_min + STEP_MINUTES,
            action=Action.EXTEND,
            sleep_efficiency=efficiency,
            nights_used=len(complete),
            reason="You are sleeping through most of your time in bed. Fifteen minutes more.",
        )

    if efficiency >= HOLD_AT:
        return TitrationResult(
            window_minutes=current_window_min,
            action=Action.HOLD,
            sleep_efficiency=efficiency,
            nights_used=len(complete),
            reason="Holding steady this week.",
        )

    # Invariant 1 — compression is refused at the floor.
    proposed = current_window_min - STEP_MINUTES
    if proposed < FLOOR_MINUTES:
        return TitrationResult(
            window_minutes=max(current_window_min, FLOOR_MINUTES),
            action=Action.FLOOR_REACHED,
            sleep_efficiency=efficiency,
            nights_used=len(complete),
            reason=(
                "Your window is already at five and a half hours, which is as "
                "low as this goes. If sleep is still broken, that is worth "
                "talking to a doctor about rather than compressing further."
            ),
        )

    return TitrationResult(
        window_minutes=proposed,
        action=Action.COMPRESS,
        sleep_efficiency=efficiency,
        nights_used=len(complete),
        reason="Fifteen minutes tighter, to concentrate your sleep.",
    )


def compression_schedule(
    start_window_min: int, target_window_min: int, days: int
) -> list[int]:
    """Step from start to target by 15 minutes every 3 days (§5.3).

    Gradual rather than in one step: the single-step version is what makes
    clinical restriction hard to tolerate, and tolerability is the whole reason
    a consumer adaptation exists.
    """
    target = max(target_window_min, FLOOR_MINUTES)
    out: list[int] = []
    window = max(start_window_min, FLOOR_MINUTES)
    for day in range(days):
        if day > 0 and day % 3 == 0 and window > target:
            window = max(target, window - STEP_MINUTES)
        out.append(window)
    return out
