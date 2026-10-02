"""
Unit tests — circular statistics for anchor stability (Habit Engine §3.1).

The midnight-spanning case is the acceptance criterion:
  Input: [23:50, 00:10]
  Expected: MAD ≈ 10 minutes (not ≈ 718 minutes as naive std would give)
"""
from __future__ import annotations

from datetime import time

import pytest

from src.habits.stability import (
    TEMPORAL_STABLE_MIN,
    score_temporal,
    score_locational,
    score_calendar,
    overall_level,
    _circular_mad_minutes,
)


class TestCircularMAD:
    def test_midnight_spanning_acceptance_criterion(self):
        """
        Critical acceptance criterion from Habit Engine §3.1.
        23:50 and 00:10 are 20 minutes apart — MAD should be ≈ 10 min,
        NOT ≈ 718 min (which naive std would return).
        """
        times = [time(23, 50), time(0, 10)]
        mad = _circular_mad_minutes(times)
        assert mad < 15, (
            f"Midnight-crossover circular MAD failed. Got {mad:.1f} min, expected ≈ 10 min. "
            "Naive std would give ≈ 718 min. This must use circular statistics."
        )

    def test_stable_times_low_mad(self):
        """07:00 cluster every day should score near-zero MAD."""
        times = [time(7, 0), time(7, 5), time(6, 58), time(7, 2), time(7, 3)]
        mad = _circular_mad_minutes(times)
        assert mad < 10

    def test_variable_times_medium_mad(self):
        """30–60 min spread should be in variable range."""
        times = [
            time(7, 0), time(7, 30), time(6, 30), time(7, 45), time(6, 15),
            time(7, 10), time(7, 50), time(6, 40),
        ]
        mad = _circular_mad_minutes(times)
        assert 20 < mad < 75

    def test_unstable_times_high_mad(self):
        """Highly scattered times should score unstable."""
        times = [
            time(6, 0), time(9, 0), time(12, 0), time(15, 0), time(18, 0),
        ]
        mad = _circular_mad_minutes(times)
        assert mad > 75


class TestScoreTemporal:
    def test_fewer_than_5_observations_is_unscored(self):
        score = score_temporal([time(7, 0)] * 4)
        assert score.level == "unscored"
        assert score.basis == "prior"

    def test_stable_anchor(self):
        times = [time(7, i) for i in range(10)]  # 07:00–07:09
        score = score_temporal(times)
        assert score.level == "stable"

    def test_unstable_anchor(self):
        import random
        random.seed(42)
        times = [time(random.randint(0, 23), random.randint(0, 59)) for _ in range(10)]
        score = score_temporal(times)
        # Scattered times should score variable or unstable
        assert score.level in ("variable", "unstable")


class TestOverallLevel:
    def test_worst_dimension_wins(self):
        from src.habits.stability import StabilityScore
        temporal = StabilityScore(level="stable", value=10.0, basis="observed", observation_count=10)
        locational = StabilityScore(level="unstable", value=0.3, basis="observed", observation_count=10)
        assert overall_level(temporal, locational) == "unstable"

    def test_all_unscored_returns_unscored(self):
        from src.habits.stability import StabilityScore
        temporal = StabilityScore(level="unscored", value=None, basis="prior", observation_count=3)
        assert overall_level(temporal) == "unscored"
