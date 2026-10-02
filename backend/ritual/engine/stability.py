"""Cue-stability scoring.

Implements SPEC-habit-engine-v1 §3.

Two rules from the spec drive the whole module:

1. **Report the weakest dimension, never a composite** (§3.1). We cannot
   validate weights for an average, and averaging hides the actionable part.
2. **Placement is creation and re-planning only** (D11). Nothing here may be
   rendered in the recovery-break surface: the same sentence is help before you
   commit and a verdict on your life afterwards.

Callers are responsible for rule 2. This module has no opinion about where its
output is displayed, which is exactly why the failure-layer acceptance criteria
check for its absence rather than trusting convention.
"""

from __future__ import annotations

import math
from datetime import datetime, time
from statistics import median
from typing import Optional, Sequence

from .models import AnchorClass, Stability, StabilityBasis, StabilityReport

SECONDS_PER_DAY = 86_400

#: Below this, no observed verdict at all (§3.2).
MIN_SAMPLES = 5
#: Below this, the verdict is provisional and uses widened temporal thresholds.
FULL_SAMPLES = 14

TEMPORAL_STABLE_MIN = 30.0
TEMPORAL_VARIABLE_MIN = 75.0
TEMPORAL_STABLE_MIN_PROVISIONAL = 45.0

LOCATION_STABLE = 0.75
LOCATION_VARIABLE = 0.50

CALENDAR_STABLE = 0.70
CALENDAR_VARIABLE = 0.45

#: §3.4. Defaults to be replaced by observation, not findings. Validate against
#: our own cohort at 6 months and update — a §8.8 candidate.
CLASS_PRIORS: dict[AnchorClass, Stability] = {
    AnchorClass.WAKE: Stability.STABLE,
    AnchorClass.FIRST_COFFEE: Stability.STABLE,
    AnchorClass.COMMUTE_START: Stability.STABLE,  # weekdays only; caller flags
    AnchorClass.BEDTIME: Stability.VARIABLE,
    AnchorClass.WORK_END: Stability.VARIABLE,
    AnchorClass.LUNCH: Stability.VARIABLE,
    AnchorClass.DINNER: Stability.VARIABLE,
    AnchorClass.CUSTOM: Stability.UNKNOWN,
}


# --------------------------------------------------------------------------
# Circular statistics
# --------------------------------------------------------------------------


def _to_angle(t: time) -> float:
    seconds = t.hour * 3600 + t.minute * 60 + t.second
    return 2 * math.pi * seconds / SECONDS_PER_DAY


def circular_mean_time(times: Sequence[time]) -> time:
    """Mean time of day, computed on the circle.

    Times of day wrap at midnight. A naive arithmetic mean of 23:50 and 00:10
    returns 12:00, which is not merely imprecise but the opposite of the truth.
    """
    if not times:
        raise ValueError("no times given")
    angles = [_to_angle(t) for t in times]
    c = sum(math.cos(a) for a in angles) / len(angles)
    s = sum(math.sin(a) for a in angles) / len(angles)
    if abs(c) < 1e-12 and abs(s) < 1e-12:
        # Perfectly antipodal sample: the mean is undefined on the circle.
        # Fall back to the first observation rather than inventing a direction.
        return times[0]
    mean_angle = math.atan2(s, c) % (2 * math.pi)
    seconds = int(round(mean_angle / (2 * math.pi) * SECONDS_PER_DAY)) % SECONDS_PER_DAY
    return time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)


def circular_mad_minutes(times: Sequence[time]) -> float:
    """Median absolute deviation about the circular mean, in minutes.

    Median rather than standard deviation for robustness: one 3am outlier in a
    fortnight of 07:00s should not condemn an anchor.
    """
    if not times:
        raise ValueError("no times given")
    mean_angle = _to_angle(circular_mean_time(times))
    deviations = []
    for t in times:
        diff = (_to_angle(t) - mean_angle + math.pi) % (2 * math.pi) - math.pi
        deviations.append(abs(diff) / (2 * math.pi) * 1440.0)
    return float(median(deviations))


# --------------------------------------------------------------------------
# Per-dimension verdicts
# --------------------------------------------------------------------------


def temporal_stability(times: Sequence[time]) -> tuple[Stability, bool]:
    """Returns (verdict, provisional).

    The MAD is rounded to a tenth of a minute before classification. Without it,
    a genuine 75-minute spread computes to 75.000000000000014 through the
    trigonometric round trip and lands in *unstable* rather than *variable* — a
    boundary the spec explicitly assigns to variable. Six seconds is well below
    any resolution we would claim, so rounding costs nothing and removes a class
    of bug that only ever appears on exact-threshold data.
    """
    n = len(times)
    if n < MIN_SAMPLES:
        return Stability.UNKNOWN, True
    provisional = n < FULL_SAMPLES
    mad = round(circular_mad_minutes(times), 1)
    stable_cut = TEMPORAL_STABLE_MIN_PROVISIONAL if provisional else TEMPORAL_STABLE_MIN
    if mad < stable_cut:
        return Stability.STABLE, provisional
    if mad <= TEMPORAL_VARIABLE_MIN:
        return Stability.VARIABLE, provisional
    return Stability.UNSTABLE, provisional


def locational_stability(modal_cluster_share: Optional[float]) -> Stability:
    """From the share of occurrences in the modal on-device location cluster.

    Only this scalar leaves the phone — never coordinates, never a centroid
    (§3.5). If location permission is denied the caller passes ``None`` and the
    dimension is simply absent; we say nothing about it.
    """
    if modal_cluster_share is None:
        return Stability.UNKNOWN
    if modal_cluster_share > LOCATION_STABLE:
        return Stability.STABLE
    if modal_cluster_share >= LOCATION_VARIABLE:
        return Stability.VARIABLE
    return Stability.UNSTABLE


def calendar_stability(same_shape_share: Optional[float]) -> Stability:
    """From the share of days whose surrounding 60-minute block has the same
    free/busy shape."""
    if same_shape_share is None:
        return Stability.UNKNOWN
    if same_shape_share > CALENDAR_STABLE:
        return Stability.STABLE
    if same_shape_share >= CALENDAR_VARIABLE:
        return Stability.VARIABLE
    return Stability.UNSTABLE


# --------------------------------------------------------------------------
# Composite report (weakest dimension)
# --------------------------------------------------------------------------

_SEVERITY = {
    Stability.STABLE: 0,
    Stability.VARIABLE: 1,
    Stability.UNSTABLE: 2,
    Stability.UNKNOWN: -1,  # never "the weakest"; absence is not a verdict
}


def score_anchor(
    anchor_class: AnchorClass,
    *,
    completion_times: Sequence[time] = (),
    modal_cluster_share: Optional[float] = None,
    calendar_same_shape_share: Optional[float] = None,
) -> StabilityReport:
    """Produce the user-facing stability verdict for an anchor.

    Falls back through observed → calendar → class prior, and always records
    which of those it used. The basis is shown to the user (§3.2): we never
    imply a prior is an observation.
    """
    temporal, provisional = temporal_stability(completion_times)
    locational = locational_stability(modal_cluster_share)
    calendar = calendar_stability(calendar_same_shape_share)

    detail = {
        "temporal": temporal,
        "locational": locational,
        "calendar": calendar,
    }
    known = {k: v for k, v in detail.items() if v is not Stability.UNKNOWN}

    if temporal is not Stability.UNKNOWN:
        basis = StabilityBasis.OBSERVED
    elif calendar is not Stability.UNKNOWN:
        basis = StabilityBasis.CALENDAR
    else:
        basis = StabilityBasis.PRIOR

    if basis is StabilityBasis.PRIOR:
        return StabilityReport(
            verdict=CLASS_PRIORS.get(anchor_class, Stability.UNKNOWN),
            basis=basis,
            weakest_dimension=None,
            detail=detail,
            sample_size=len(completion_times),
            provisional=True,
        )

    weakest_dim = max(known, key=lambda k: _SEVERITY[known[k]])
    return StabilityReport(
        verdict=known[weakest_dim],
        basis=basis,
        weakest_dimension=weakest_dim,
        detail=detail,
        sample_size=len(completion_times),
        provisional=provisional and basis is StabilityBasis.OBSERVED,
    )
