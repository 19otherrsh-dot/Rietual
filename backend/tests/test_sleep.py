"""Sleep Reset titration — safety invariants.

PLAN-phase1-v1 §7 requires that the window algorithm "cannot propose < 5.5
hours, under adversarial diary data". These tests are that gate, and they are
written adversarially on purpose: the diary is self-reported, and a distressed
user reporting three hours of sleep must not be handed a three-and-a-half hour
window by a correct-looking algorithm.
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from ritual.journeys.sleep import (
    FLOOR_MINUTES,
    Action,
    SleepNight,
    compression_schedule,
    initial_window,
    sleep_efficiency,
    titrate,
)

D0 = date(2026, 6, 1)


def nights(efficiency: float, count: int = 5, in_bed: int = 480) -> list[SleepNight]:
    return [
        SleepNight(D0 + timedelta(days=i), in_bed, int(in_bed * efficiency))
        for i in range(count)
    ]


class TestFloorInvariant(unittest.TestCase):
    """Invariant 1: the algorithm may never propose below 5.5 hours."""

    def test_initial_window_respects_floor_on_extreme_report(self):
        self.assertEqual(initial_window(180), FLOOR_MINUTES)  # "3 hours"
        self.assertEqual(initial_window(0), FLOOR_MINUTES)
        self.assertEqual(initial_window(-60), FLOOR_MINUTES)  # corrupt input

    def test_initial_window_is_measured_sleep_plus_thirty(self):
        self.assertEqual(initial_window(420), 450)

    def test_repeated_compression_never_breaches_the_floor(self):
        """Adversarial: sustained terrible efficiency, forty weeks running."""
        window = 480
        for _ in range(40):
            result = titrate(window, nights(0.40))
            window = result.window_minutes
            self.assertGreaterEqual(
                window, FLOOR_MINUTES, "floor breached during compression"
            )
        self.assertEqual(window, FLOOR_MINUTES)

    def test_at_the_floor_the_action_says_so(self):
        result = titrate(FLOOR_MINUTES, nights(0.40))
        self.assertIs(result.action, Action.FLOOR_REACHED)
        self.assertEqual(result.window_minutes, FLOOR_MINUTES)
        self.assertIn("doctor", result.reason)

    def test_a_window_already_below_the_floor_is_raised_not_lowered(self):
        """Defensive: bad stored state must not be compounded."""
        result = titrate(300, nights(0.40))
        self.assertGreaterEqual(result.window_minutes, FLOOR_MINUTES)


class TestSleepinessOverride(unittest.TestCase):
    """Invariant 2: sleepiness beats efficiency, always."""

    def test_override_extends_even_when_efficiency_says_compress(self):
        result = titrate(420, nights(0.40), severe_sleepiness=True)
        self.assertIs(result.action, Action.SLEEPINESS_OVERRIDE)
        self.assertEqual(result.window_minutes, 450)

    def test_override_fires_even_with_missing_data(self):
        """The one case where we act without a full diary — extending is safe."""
        sparse = [SleepNight(D0, None, None)] * 5
        result = titrate(420, sparse, severe_sleepiness=True)
        self.assertIs(result.action, Action.SLEEPINESS_OVERRIDE)
        self.assertEqual(result.window_minutes, 450)

    def test_override_fires_at_the_floor(self):
        result = titrate(FLOOR_MINUTES, nights(0.95), severe_sleepiness=True)
        self.assertEqual(result.window_minutes, FLOOR_MINUTES + 30)


class TestNeverImpute(unittest.TestCase):
    """Invariant 3: hold rather than guess."""

    def test_two_missing_nights_pauses_titration(self):
        data = nights(0.95, count=3) + [SleepNight(D0, None, None)] * 2
        result = titrate(420, data)
        self.assertIs(result.action, Action.PAUSED_MISSING_DATA)
        self.assertEqual(result.window_minutes, 420, "window must hold")

    def test_one_missing_night_still_titrates(self):
        data = nights(0.95, count=4) + [SleepNight(D0, None, None)]
        result = titrate(420, data)
        self.assertIs(result.action, Action.EXTEND)

    def test_zero_time_in_bed_is_not_a_valid_night(self):
        data = nights(0.95, count=3) + [
            SleepNight(D0, 0, 0),
            SleepNight(D0, 0, 0),
        ]
        self.assertIs(titrate(420, data).action, Action.PAUSED_MISSING_DATA)


class TestTitrationBands(unittest.TestCase):
    def test_high_efficiency_extends(self):
        result = titrate(420, nights(0.93))
        self.assertIs(result.action, Action.EXTEND)
        self.assertEqual(result.window_minutes, 435)

    def test_middle_band_holds(self):
        result = titrate(420, nights(0.87))
        self.assertIs(result.action, Action.HOLD)
        self.assertEqual(result.window_minutes, 420)

    def test_low_efficiency_compresses(self):
        result = titrate(420, nights(0.70))
        self.assertIs(result.action, Action.COMPRESS)
        self.assertEqual(result.window_minutes, 405)

    def test_boundaries(self):
        self.assertIs(titrate(420, nights(0.90)).action, Action.EXTEND)
        self.assertIs(titrate(420, nights(0.85)).action, Action.HOLD)
        self.assertIs(titrate(420, nights(0.8499)).action, Action.COMPRESS)

    def test_efficiency_uses_only_complete_nights(self):
        data = nights(0.9, count=4) + [SleepNight(D0, None, None)]
        self.assertAlmostEqual(sleep_efficiency(data), 0.9, places=3)

    def test_efficiency_of_no_data_is_none(self):
        self.assertIsNone(sleep_efficiency([SleepNight(D0, None, None)]))


class TestCompressionSchedule(unittest.TestCase):
    def test_steps_fifteen_minutes_every_three_days(self):
        sched = compression_schedule(480, 420, days=13)
        self.assertEqual(sched[0], 480)
        self.assertEqual(sched[3], 465)
        self.assertEqual(sched[6], 450)
        self.assertEqual(sched[12], 420)

    def test_never_below_the_floor(self):
        sched = compression_schedule(480, 120, days=60)
        self.assertEqual(min(sched), FLOOR_MINUTES)

    def test_does_not_overshoot_the_target(self):
        sched = compression_schedule(450, 420, days=30)
        self.assertEqual(min(sched), 420)


if __name__ == "__main__":
    unittest.main()
