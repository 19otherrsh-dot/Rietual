"""
Unit tests — instrument scoring functions.

All pure function tests — no DB, no network.
"""
from __future__ import annotations

import pytest
from datetime import time

from src.instruments.srbai import SRBAI_GRADUATION_THRESHOLD, score as srbai_score
from src.instruments.who5 import score as who5_score
from src.instruments.mctq import score_quick as mctq_quick
from src.instruments.breq3 import score as breq3_score
from src.instruments.pss10 import score as pss10_score, PSS10_REVERSE_ITEMS


class TestSRBAI:
    def test_max_score(self):
        result = srbai_score([7, 7, 7, 7])
        assert result.mean_score == 7.0
        assert result.above_threshold is True

    def test_min_score(self):
        result = srbai_score([1, 1, 1, 1])
        assert result.mean_score == 1.0
        assert result.above_threshold is False

    def test_threshold_boundary(self):
        # Mean = 5.5 exactly → above threshold
        result = srbai_score([5, 6, 5, 6])
        assert result.mean_score == 5.5
        assert result.above_threshold is True

    def test_below_threshold(self):
        result = srbai_score([5, 5, 5, 5])
        assert result.above_threshold is False  # 5.0 < 5.5

    def test_wrong_item_count(self):
        with pytest.raises(ValueError, match="exactly 4"):
            srbai_score([7, 7, 7])

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            srbai_score([8, 7, 7, 7])


class TestWHO5:
    def test_max_score_is_100_percent(self):
        result = who5_score([5, 5, 5, 5, 5])
        assert result.raw_total == 25
        assert result.percentage_score == 100.0

    def test_zero_score(self):
        result = who5_score([0, 0, 0, 0, 0])
        assert result.percentage_score == 0.0

    def test_mid_score(self):
        result = who5_score([3, 3, 3, 3, 3])
        assert result.raw_total == 15
        assert result.percentage_score == 60.0

    def test_wrong_item_count(self):
        with pytest.raises(ValueError, match="exactly 5"):
            who5_score([5, 5, 5, 5])


class TestMCTQ:
    def test_simple_chronotype(self):
        result = mctq_quick(time(23, 0), time(7, 0))  # 23:00 → 07:00
        assert result.sleep_duration_free_hours == pytest.approx(8.0, abs=0.01)
        # Mid-sleep at 03:00 → 3.0 hours
        assert result.mid_sleep_free_hours == pytest.approx(3.0, abs=0.1)
        assert result.chronotype_label == "intermediate"

    def test_midnight_crossover(self):
        """The critical case: sleep 23:50, wake 00:10 → duration ~20 min, MSF ~00:00."""
        result = mctq_quick(time(23, 50), time(0, 10))
        assert result.sleep_duration_free_hours == pytest.approx(20 / 60, abs=0.02)
        # Mid-sleep should be near midnight, NOT near 12:00
        assert result.mid_sleep_free_hours < 1.0 or result.mid_sleep_free_hours > 23.0

    def test_late_chronotype(self):
        result = mctq_quick(time(2, 0), time(10, 0))
        assert result.chronotype_label == "late"

    def test_early_chronotype(self):
        result = mctq_quick(time(21, 0), time(5, 0))
        assert result.chronotype_label == "early"


class TestBREQ3:
    def test_fully_autonomous(self):
        result = breq3_score(
            intrinsic=[4, 4, 4],
            identified=[4, 4, 4],
            introjected=[0, 0, 0],
            external=[0, 0, 0],
        )
        assert result.autonomous_motivation_index == pytest.approx(4.0, abs=0.01)

    def test_fully_controlled(self):
        result = breq3_score(
            intrinsic=[0, 0, 0],
            identified=[0, 0, 0],
            introjected=[4, 4, 4],
            external=[4, 4, 4],
        )
        assert result.autonomous_motivation_index == pytest.approx(-4.0, abs=0.01)

    def test_neutral(self):
        result = breq3_score(
            intrinsic=[2, 2, 2],
            identified=[2, 2, 2],
            introjected=[2, 2, 2],
            external=[2, 2, 2],
        )
        assert result.autonomous_motivation_index == pytest.approx(0.0, abs=0.01)

    def test_wrong_subscale_count(self):
        with pytest.raises(ValueError):
            breq3_score([4, 4], [4, 4, 4], [0, 0, 0], [0, 0, 0])


class TestPSS10:
    def test_max_stress(self):
        # Items 4,5,7,8 are reverse-scored; answer 0 on those = stress=4
        raw = [4, 4, 4, 0, 0, 4, 0, 0, 4, 4]
        result = pss10_score(raw)
        assert result.total_score == 40

    def test_min_stress(self):
        raw = [0, 0, 0, 4, 4, 0, 4, 4, 0, 0]
        result = pss10_score(raw)
        assert result.total_score == 0

    def test_reverse_items(self):
        """Items 4,5,7,8 (1-indexed) must be reverse scored."""
        assert PSS10_REVERSE_ITEMS == {4, 5, 7, 8}

    def test_wrong_item_count(self):
        with pytest.raises(ValueError, match="exactly 10"):
            pss10_score([0] * 9)
