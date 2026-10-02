"""
SRBAI — Self-Report Behavioural Automaticity Index.

4-item scale, 1–7 each.  Score = mean of all four items.
Used as the primary automaticity measure (PRD §4.6.1, §4.6.4).

Graduation criterion: SRBAI at or above threshold on two consecutive
biweekly measures (Habit Engine §9.1).

Items (Gardner et al. 2012):
  1. [Habit] is something I do automatically.
  2. [Habit] is something I do without thinking.
  3. [Habit] is something I do without having to consciously remember.
  4. [Habit] is something that makes me feel weird if I don't do it.
"""
from __future__ import annotations

from dataclasses import dataclass

from ritual.engine.graduation import SRBAI_THRESHOLD


SRBAI_MIN = 1
SRBAI_MAX = 7
SRBAI_ITEMS = 4

# Graduation threshold: >=5.5 on two consecutive biweekly measures
# (conservative; validate against our own cohort at 6 months — Habit Engine §10).
#
# Sourced from the domain core rather than redeclared. Graduation is D10 and
# the rule that decides it belongs in one place; two copies of 5.5 in two
# packages is a silent drift waiting to happen the first time the cohort data
# says it should move.
SRBAI_GRADUATION_THRESHOLD = SRBAI_THRESHOLD


@dataclass
class SRBAIResult:
    raw_scores: list[int]      # individual item scores (1–7 each)
    mean_score: float          # primary output
    above_threshold: bool      # True if ≥ SRBAI_GRADUATION_THRESHOLD


def score(raw: list[int]) -> SRBAIResult:
    """
    Score an SRBAI response.

    Args:
        raw: List of 4 integers, each 1–7.

    Raises:
        ValueError: If the input doesn't have exactly 4 items or items are out of range.
    """
    if len(raw) != SRBAI_ITEMS:
        raise ValueError(f"SRBAI requires exactly {SRBAI_ITEMS} items; got {len(raw)}.")
    for i, v in enumerate(raw, 1):
        if not (SRBAI_MIN <= v <= SRBAI_MAX):
            raise ValueError(
                f"SRBAI item {i} out of range: {v} (must be {SRBAI_MIN}–{SRBAI_MAX})."
            )
    mean = sum(raw) / SRBAI_ITEMS
    return SRBAIResult(
        raw_scores=raw,
        mean_score=round(mean, 4),
        above_threshold=mean >= SRBAI_GRADUATION_THRESHOLD,
    )
