"""
WHO-5 Wellbeing Index.

5 items, 0–5 each.
Raw score = sum (0–25).
Percentage score = (raw / 25) × 100.

Phase 1 primary wellbeing measure (PRD §4.6.1, D12).
Framing at collection: "So you can see what moved" (Onboarding §5.4).

Note: WHO-5 is a wellbeing measure, not a clinical screener. It carries no
duty we cannot currently meet — which is exactly why PHQ-8/GAD-7 were removed
from Phase 1 (D12). Do not add clinical interpretation logic to this function.
"""
from __future__ import annotations

from dataclasses import dataclass


WHO5_ITEMS = 5
WHO5_ITEM_MIN = 0
WHO5_ITEM_MAX = 5
# Below 50% (raw < 13) is typically considered poor wellbeing in the literature.
# Do NOT display this threshold to users in Phase 1.
WHO5_LOW_WELLBEING_RAW = 13


@dataclass
class WHO5Result:
    raw_scores: list[int]
    raw_total: int          # 0–25
    percentage_score: float  # 0–100


def score(raw: list[int]) -> WHO5Result:
    if len(raw) != WHO5_ITEMS:
        raise ValueError(f"WHO-5 requires exactly {WHO5_ITEMS} items; got {len(raw)}.")
    for i, v in enumerate(raw, 1):
        if not (WHO5_ITEM_MIN <= v <= WHO5_ITEM_MAX):
            raise ValueError(
                f"WHO-5 item {i} out of range: {v} (must be {WHO5_ITEM_MIN}–{WHO5_ITEM_MAX})."
            )
    total = sum(raw)
    return WHO5Result(
        raw_scores=raw,
        raw_total=total,
        percentage_score=round((total / 25) * 100, 1),
    )
