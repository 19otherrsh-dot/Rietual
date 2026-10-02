"""
BREQ-3 — Behavioural Regulation in Exercise Questionnaire-3 (subset).

Used to measure motivation quality (autonomous vs. controlled regulation).
Phase 1 uses a subset sufficient to compute the autonomous/controlled ratio.

Subscales used:
  - Intrinsic regulation (3 items, 0–4 each)
  - Identified regulation (3 items, 0–4 each)
  - Introjected regulation (3 items, 0–4 each)
  - External regulation (3 items, 0–4 each)

Autonomous motivation index (AMI) = mean(intrinsic + identified) − mean(introjected + external)
Positive AMI → autonomous motivation (better for long-term adherence).

Reference: Markland & Tobin 2004; PRD §4.6.1.
Cadence: Monthly. Collected at day 14 per Onboarding §5.4.
"""
from __future__ import annotations

from dataclasses import dataclass


BREQ3_ITEM_MIN = 0
BREQ3_ITEM_MAX = 4
BREQ3_ITEMS_PER_SUBSCALE = 3


@dataclass
class BREQ3Result:
    intrinsic_mean: float
    identified_mean: float
    introjected_mean: float
    external_mean: float
    autonomous_motivation_index: float   # positive = more autonomous


def _subscale_mean(items: list[int], name: str) -> float:
    if len(items) != BREQ3_ITEMS_PER_SUBSCALE:
        raise ValueError(
            f"BREQ-3 {name} subscale requires {BREQ3_ITEMS_PER_SUBSCALE} items; got {len(items)}."
        )
    for i, v in enumerate(items, 1):
        if not (BREQ3_ITEM_MIN <= v <= BREQ3_ITEM_MAX):
            raise ValueError(
                f"BREQ-3 {name} item {i} out of range: {v} "
                f"(must be {BREQ3_ITEM_MIN}–{BREQ3_ITEM_MAX})."
            )
    return sum(items) / len(items)


def score(
    intrinsic: list[int],
    identified: list[int],
    introjected: list[int],
    external: list[int],
) -> BREQ3Result:
    intr = _subscale_mean(intrinsic, "intrinsic")
    iden = _subscale_mean(identified, "identified")
    intro = _subscale_mean(introjected, "introjected")
    ext = _subscale_mean(external, "external")

    ami = (intr + iden) / 2 - (intro + ext) / 2

    return BREQ3Result(
        intrinsic_mean=round(intr, 4),
        identified_mean=round(iden, 4),
        introjected_mean=round(intro, 4),
        external_mean=round(ext, 4),
        autonomous_motivation_index=round(ami, 4),
    )
