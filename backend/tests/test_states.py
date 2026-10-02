"""Lapse state machine and recovery surfacing.

The tests that matter most here are the D1 ones: a first miss must produce
nothing user-visible unless the user came looking.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ritual.engine.models import HabitState, Outcome
from ritual.engine.states import (
    LapseCounters,
    RecoverySurface,
    Trigger,
    apply_outcome,
    check_idle,
    is_bad_week,
    lapse_recovery_rate,
    recovery_surface,
    should_offer_woop,
)

TZ = ZoneInfo("Europe/London")
T0 = datetime(2026, 6, 1, 9, 0, tzinfo=TZ)


def surface(state, trigger, **kw):
    params = dict(now=T0, counters=LapseCounters())
    params.update(kw)
    return recovery_surface(state, trigger, **params)


# ---------------------------------------------------------------------------
# Gate: first miss produces nothing user-visible unless the user opens the app
# ---------------------------------------------------------------------------


class TestD1FirstMissSilence(unittest.TestCase):
    def test_one_miss_is_silent_on_push(self):
        """The whole point. We do not tell someone they failed."""
        self.assertIs(
            surface(HabitState.LAPSED_1, Trigger.PUSH), RecoverySurface.NONE
        )

    def test_one_miss_is_answered_on_pull(self):
        """A user who opened the app has come looking. Leaving an
        unacknowledged gap on the screen is its own small unkindness."""
        self.assertIs(
            surface(HabitState.LAPSED_1, Trigger.PULL), RecoverySurface.LIGHT_ACK
        )

    def test_second_miss_surfaces_on_both(self):
        for trigger in (Trigger.PUSH, Trigger.PULL):
            self.assertIs(
                surface(HabitState.LAPSED_2, trigger), RecoverySurface.FULL_BREAK
            )

    def test_light_ack_is_not_subject_to_the_daily_break_cap(self):
        """The cap governs recovery *breaks*. An inline card acknowledgment is
        not one, and suppressing it would reintroduce the unacknowledged gap."""
        self.assertIs(
            surface(HabitState.LAPSED_1, Trigger.PULL, breaks_shown_today=5),
            RecoverySurface.LIGHT_ACK,
        )


class TestSurfaceSuppression(unittest.TestCase):
    def test_inert_states_surface_nothing(self):
        for state in (HabitState.PAUSED, HabitState.GRADUATED, HabitState.RETIRED):
            for trigger in (Trigger.PUSH, Trigger.PULL):
                self.assertIs(surface(state, trigger), RecoverySurface.NONE, state)

    def test_healthy_habit_surfaces_nothing(self):
        self.assertIs(surface(HabitState.FORMING, Trigger.PULL), RecoverySurface.NONE)

    def test_bad_week_overrides_everything(self):
        """One whole-account message, not six individual ones."""
        self.assertIs(
            surface(HabitState.LAPSED_2, Trigger.PULL, bad_week=True),
            RecoverySurface.BAD_WEEK,
        )

    def test_bad_week_suppresses_even_the_light_ack(self):
        self.assertIs(
            surface(HabitState.LAPSED_1, Trigger.PULL, bad_week=True),
            RecoverySurface.BAD_WEEK,
        )

    def test_three_dismissals_suppress_for_that_habit(self):
        self.assertIs(
            surface(HabitState.LAPSED_2, Trigger.PULL, dismissals=3),
            RecoverySurface.NONE,
        )

    def test_daily_cap_applies_to_full_breaks(self):
        self.assertIs(
            surface(HabitState.LAPSED_2, Trigger.PULL, breaks_shown_today=2),
            RecoverySurface.NONE,
        )

    def test_per_habit_72h_cap(self):
        counters = LapseCounters(last_break_at=T0 - timedelta(hours=10))
        self.assertIs(
            surface(HabitState.LAPSED_2, Trigger.PULL, counters=counters),
            RecoverySurface.NONE,
        )

    def test_dormant_return_surface(self):
        self.assertIs(
            surface(HabitState.DORMANT, Trigger.PULL), RecoverySurface.DORMANT_RETURN
        )


class TestBadWeek(unittest.TestCase):
    def test_five_misses_in_48h(self):
        misses = [T0 - timedelta(hours=h) for h in (1, 5, 12, 20, 40)]
        self.assertTrue(is_bad_week(misses, T0))

    def test_four_is_not_a_bad_week(self):
        misses = [T0 - timedelta(hours=h) for h in (1, 5, 12, 20)]
        self.assertFalse(is_bad_week(misses, T0))

    def test_old_misses_do_not_count(self):
        misses = [T0 - timedelta(hours=h) for h in (1, 5, 60, 70, 80)]
        self.assertFalse(is_bad_week(misses, T0))


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


class TestTransitions(unittest.TestCase):
    def test_misses_deepen_lapse(self):
        state, counters = HabitState.FORMING, LapseCounters()
        expected = [
            HabitState.LAPSED_1,
            HabitState.LAPSED_2,
            HabitState.LAPSED_2,
            HabitState.DORMANT,
        ]
        for day, want in enumerate(expected):
            state, counters, _ = apply_outcome(
                state, counters, Outcome.MISSED, T0 + timedelta(days=day)
            )
            self.assertIs(state, want, f"after {day + 1} misses")

    def test_probe_miss_does_not_deepen_lapse(self):
        """We withheld the prompt, so we absorb it."""
        state, counters = HabitState.FORMING, LapseCounters()
        for day in range(5):
            state, counters, _ = apply_outcome(
                state, counters, Outcome.PROBE_MISS, T0 + timedelta(days=day)
            )
        self.assertIs(state, HabitState.FORMING)
        self.assertEqual(counters.consecutive_misses, 0)

    def test_skip_does_not_deepen_lapse(self):
        """A user who told us they were not doing it has not failed."""
        state, counters = HabitState.FORMING, LapseCounters()
        for day in range(5):
            state, counters, _ = apply_outcome(
                state, counters, Outcome.SKIPPED, T0 + timedelta(days=day)
            )
        self.assertIs(state, HabitState.FORMING)

    def test_completion_within_72h_emits_recovered(self):
        state, counters = HabitState.FORMING, LapseCounters()
        state, counters, _ = apply_outcome(state, counters, Outcome.MISSED, T0)
        state, counters, events = apply_outcome(
            state, counters, Outcome.COMPLETED, T0 + timedelta(hours=20)
        )
        self.assertIn("recovered", events)
        self.assertIs(state, HabitState.FORMING)
        self.assertEqual(counters.consecutive_misses, 0)

    def test_deep_recovery_emits_its_own_event(self):
        state, counters = HabitState.FORMING, LapseCounters()
        for day in range(2):
            state, counters, _ = apply_outcome(
                state, counters, Outcome.MISSED, T0 + timedelta(days=day)
            )
        _, _, events = apply_outcome(
            state, counters, Outcome.COMPLETED, T0 + timedelta(days=2)
        )
        self.assertIn("recovered_deep", events)

    def test_completion_after_72h_resets_without_a_recovery_event(self):
        state, counters = HabitState.FORMING, LapseCounters()
        state, counters, _ = apply_outcome(state, counters, Outcome.MISSED, T0)
        state, counters, events = apply_outcome(
            state, counters, Outcome.COMPLETED, T0 + timedelta(hours=100)
        )
        self.assertNotIn("recovered", events)
        self.assertEqual(counters.consecutive_misses, 0)

    def test_paused_is_inert(self):
        """Every lapse rule checks paused first (SPEC-failure-layer §2.1)."""
        state, counters, events = apply_outcome(
            HabitState.PAUSED, LapseCounters(), Outcome.MISSED, T0
        )
        self.assertIs(state, HabitState.PAUSED)
        self.assertEqual(events, [])
        self.assertEqual(counters.consecutive_misses, 0)


class TestIdle(unittest.TestCase):
    def test_ten_idle_days_goes_dormant(self):
        counters = LapseCounters(last_interaction_at=T0)
        state, events = check_idle(
            HabitState.LAPSED_1, counters, T0 + timedelta(days=10)
        )
        self.assertIs(state, HabitState.DORMANT)
        self.assertIn("entered_dormant", events)

    def test_retirement_is_offered_never_applied(self):
        """A habit disappearing on its own is indistinguishable from a bug."""
        counters = LapseCounters(
            last_interaction_at=T0, entered_dormant_at=T0
        )
        state, events = check_idle(
            HabitState.DORMANT, counters, T0 + timedelta(days=22)
        )
        self.assertIs(state, HabitState.DORMANT, "must not self-retire")
        self.assertIn("retirement_offer_due", events)


class TestWoopOffer(unittest.TestCase):
    def test_offered_to_quick_setup_users_at_first_lapse(self):
        self.assertTrue(
            should_offer_woop("if_then", HabitState.LAPSED_1, Trigger.PULL, LapseCounters())
        )

    def test_not_offered_to_users_who_already_did_woop(self):
        self.assertFalse(
            should_offer_woop("woop", HabitState.LAPSED_1, Trigger.PULL, LapseCounters())
        )

    def test_not_offered_on_push(self):
        self.assertFalse(
            should_offer_woop("if_then", HabitState.LAPSED_1, Trigger.PUSH, LapseCounters())
        )

    def test_not_offered_after_two_declines(self):
        self.assertFalse(
            should_offer_woop(
                "if_then",
                HabitState.LAPSED_1,
                Trigger.PULL,
                LapseCounters(woop_offers_declined=2),
            )
        )

    def test_not_offered_at_lapsed_2(self):
        """By then the recovery break's step 4 is doing this work."""
        self.assertFalse(
            should_offer_woop("if_then", HabitState.LAPSED_2, Trigger.PULL, LapseCounters())
        )


class TestHeadlineMetric(unittest.TestCase):
    def test_recovery_rate(self):
        misses = [
            (T0, T0 + timedelta(hours=20)),   # recovered
            (T0, T0 + timedelta(hours=100)),  # too late
            (T0, None),                       # never
            (T0, T0 + timedelta(hours=71)),   # just inside
        ]
        self.assertAlmostEqual(lapse_recovery_rate(misses), 0.5)

    def test_no_misses_is_none_not_zero(self):
        """Zero would read as total failure on a user who never lapsed."""
        self.assertIsNone(lapse_recovery_rate([]))


if __name__ == "__main__":
    unittest.main()
