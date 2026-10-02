"""
Anchor stability scoring — Habit Engine §3.

**This module is now a thin adapter over `ritual.engine.stability`.**

The scoring rules live in the domain core, which is framework-free and covered
by the gate suite in `tests/test_engine.py`. This file exists only to preserve
the shape the workers and routers already call (`StabilityScore`,
`score_temporal`, `worst_dimension`, `overall_level`) so nothing downstream had
to change.

Two behavioural corrections came with the move, both boundary conditions
against SPEC-habit-engine §3.1:

  * Temporal: the spec puts "30–75 min" in *variable* and ">75 min" in
    *unstable*, so a MAD of exactly 75 is variable. The previous `mad < 75`
    test classified it as unstable.
  * Locational: the spec puts "> 0.75" in *stable* and "0.5–0.75" in
    *variable*, so a share of exactly 0.75 is variable. The previous
    `share >= 0.75` test classified it as stable.

Also drops the numpy dependency: the circular statistics are ten lines of
stdlib `math`, and a numerical-computing library is a large thing to carry for
one median.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from ritual.engine.models import Stability
from ritual.engine.stability import (
    CALENDAR_STABLE,
    CALENDAR_VARIABLE,
    LOCATION_STABLE,
    LOCATION_VARIABLE,
    MIN_SAMPLES,
    calendar_stability,
    circular_mad_minutes,
    locational_stability,
    temporal_stability,
)

#: Compatibility alias. `tests/unit/test_circular_stats.py` imports the private
#: helper by its pre-merge name; the implementation now lives in the domain core.
_circular_mad_minutes = circular_mad_minutes

# ── Thresholds (re-exported for call sites that referenced them) ───────────────

TEMPORAL_STABLE_MIN = MIN_SAMPLES
TEMPORAL_STABLE_MAD_MINUTES = 30.0
TEMPORAL_VARIABLE_MAD_MINUTES = 75.0
TEMPORAL_PROVISIONAL_STABLE_MAD = 45.0

LOCATIONAL_STABLE_SHARE = LOCATION_STABLE
LOCATIONAL_VARIABLE_SHARE = LOCATION_VARIABLE

CALENDAR_STABLE_SHARE = CALENDAR_STABLE
CALENDAR_VARIABLE_SHARE = CALENDAR_VARIABLE

_UNSCORED = "unscored"

_LEVEL = {
    Stability.STABLE: "stable",
    Stability.VARIABLE: "variable",
    Stability.UNSTABLE: "unstable",
    Stability.UNKNOWN: _UNSCORED,
}


@dataclass
class StabilityScore:
    """
    Result for one dimension. Never averaged into a composite (§3.1) —
    we report the worst dimension and what to do about it.
    """

    level: str          # "stable" | "variable" | "unstable" | "unscored"
    value: float | None  # raw metric (MAD in minutes, or share 0–1)
    basis: str          # "prior" | "observed" | "provisional"
    observation_count: int


def score_temporal(times: list[time]) -> StabilityScore:
    """Temporal stability from the circular MAD of completion times."""
    n = len(times)
    verdict, provisional = temporal_stability(times)

    if verdict is Stability.UNKNOWN:
        return StabilityScore(
            level=_UNSCORED, value=None, basis="prior", observation_count=n
        )

    return StabilityScore(
        level=_LEVEL[verdict],
        value=round(circular_mad_minutes(times), 1),
        basis="provisional" if provisional else "observed",
        observation_count=n,
    )


def score_locational(cluster_share: float, observation_count: int) -> StabilityScore:
    """Locational stability from the modal on-device cluster share (§3.5).

    Only this scalar leaves the phone — never coordinates, never a centroid.
    """
    if observation_count < MIN_SAMPLES:
        return StabilityScore(
            level=_UNSCORED, value=None, basis="prior",
            observation_count=observation_count,
        )
    return StabilityScore(
        level=_LEVEL[locational_stability(cluster_share)],
        value=round(cluster_share, 3),
        basis="observed",
        observation_count=observation_count,
    )


def score_calendar(shape_share: float, observation_count: int) -> StabilityScore:
    """Calendar stability from the share of days with the same free/busy shape."""
    if observation_count < MIN_SAMPLES:
        return StabilityScore(
            level=_UNSCORED, value=None, basis="prior",
            observation_count=observation_count,
        )
    return StabilityScore(
        level=_LEVEL[calendar_stability(shape_share)],
        value=round(shape_share, 3),
        basis="observed",
        observation_count=observation_count,
    )


def worst_dimension(
    temporal: StabilityScore,
    locational: StabilityScore | None,
    calendar: StabilityScore | None,
) -> StabilityScore:
    """The worst-scoring dimension — what we surface to the user (§3.1).

    Unscored dimensions are excluded: a denied location permission must not
    read as instability.
    """
    rank = {"unstable": 0, "variable": 1, "stable": 2, _UNSCORED: 3}
    candidates = [d for d in (temporal, locational, calendar) if d is not None]
    scored = [d for d in candidates if d.level != _UNSCORED]
    if not scored:
        return temporal
    return min(scored, key=lambda d: rank[d.level])


def overall_level(
    temporal: StabilityScore,
    locational: StabilityScore | None = None,
    calendar: StabilityScore | None = None,
) -> str:
    """Label of the worst scored dimension.

    Callers must not render this in the recovery-break surface (D11): the same
    sentence is help before you commit and a verdict on your life afterwards.
    """
    return worst_dimension(temporal, locational, calendar).level
