"""
PSS-10 — Perceived Stress Scale (10-item).

Items 1–10. Items 4, 5, 7, 8 are positively worded and are reverse-scored.
Score range: 0–40. Higher = greater perceived stress.

Cadence: Day 30, then monthly (Onboarding §5.4).

Reference: Cohen, Kamarck & Mermelstein 1983; PRD §4.6.1.
"""
from __future__ import annotations

from dataclasses import dataclass

PSS10_ITEMS = 10
PSS10_ITEM_MIN = 0
PSS10_ITEM_MAX = 4
# Indices (1-based) of positively-worded items that are reverse-scored
PSS10_REVERSE_ITEMS = {4, 5, 7, 8}


@dataclass
class PSS10Result:
    raw_scores: list[int]
    total_score: int     # 0–40


def score(raw: list[int]) -> PSS10Result:
    if len(raw) != PSS10_ITEMS:
        raise ValueError(f"PSS-10 requires exactly {PSS10_ITEMS} items; got {len(raw)}.")
    for i, v in enumerate(raw, 1):
        if not (PSS10_ITEM_MIN <= v <= PSS10_ITEM_MAX):
            raise ValueError(
                f"PSS-10 item {i} out of range: {v} (must be {PSS10_ITEM_MIN}–{PSS10_ITEM_MAX})."
            )

    total = 0
    for i, v in enumerate(raw, 1):
        if i in PSS10_REVERSE_ITEMS:
            total += PSS10_ITEM_MAX - v  # reverse score
        else:
            total += v

    return PSS10Result(raw_scores=raw, total_score=total)
