"""Habit graduation — SPEC-habit-engine §9, D10.

The criteria are conjunctive and the denominator in criterion 3 is the part
most likely to be quietly wrong, so it gets the most tests: measured over all
occurrences instead of probe-eligible ones, completion rises trivially once
prompts stop, and a habit could graduate on the strength of us having stopped
asking rather than on anything the user did.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ritual.engine.graduation import (
    COMPLETION_FLOOR,
    REQUIRED_CONSECUTIVE_MEASURES,
    SRBAI_THRESHOLD,
    GraduationCheck,
    SRBAIMeasure,
    check_graduation,
    consecutive_passing_measures,
    graduation_message,
    maintenance_check_dates,
    next_measure_due,
    trailing_completion_rate,
)
from ritual.engine.models import (
    CompletionSource,
    FadeLevel,
    Habit,
    HabitState,
    Occurrence,
    Outcome,
    PromptPolicy,
)

TZ = ZoneInfo("Europe/London")
NOW = datetime(2026, 6, 30, 9, 0, tzinfo=TZ)


def make_habit(**kw) -> Habit:
    base = dict(
        id="h1",
        user_id="u1",
        title="Morning stretch",
        full_version="10 minute stretch",
        micro_version="Two shoulder rolls",
        anchor_id="a1",
        timezone="Europe/London",
        state=HabitState.ESTABLISHED,
        fade_level=FadeLevel.L4,
    )
    base.update(kw)
    return Habit(**base)


def criteria(habit: Habit) -> dict:
    """The two habit fields `check_graduation` reads.

    The core takes these rather than a Habit so the ORM layer can call it
    without building a dataclass it does not otherwise use.
    """
    return {"state": habit.state, "fade_level": habit.fade_level}


def occ(
    days_ago: int,
    *,
    completed: bool = True,
    policy: PromptPolicy = PromptPolicy.PROMPT,
    outcome: Outcome = Outcome.PENDING,
) -> Occurrence:
    scheduled = NOW - timedelta(days=days_ago)
    return Occurrence(
        id=f"o{days_ago}",
        habit_id="h1",
        scheduled_local=scheduled,
        window_start=scheduled - timedelta(minutes=90),
        window_end=scheduled + timedelta(minutes=90),
        prompt_policy=policy,
        completed_at=scheduled if completed else None,
        completion_source=CompletionSource.APP if completed else None,
        outcome=outcome,
    )


def passing_measures(n: int = 2) -> list[SRBAIMeasure]:
    return [
        SRBAIMeasure(NOW - timedelta(days=14 * i), SRBAI_THRESHOLD + 0.5)
        for i in range(n)
    ]


class TestSRBAICriterion(unittest.TestCase):
    def test_two_consecutive_passing_measures(self):
        self.assertEqual(consecutive_passing_measures(passing_measures(2)), 2)

    def test_a_failing_measure_breaks_the_streak(self):
        measures = [
            SRBAIMeasure(NOW, SRBAI_THRESHOLD + 0.5),
            SRBAIMeasure(NOW - timedelta(days=14), SRBAI_THRESHOLD - 0.1),
            SRBAIMeasure(NOW - timedelta(days=28), SRBAI_THRESHOLD + 1.0),
        ]
        self.assertEqual(consecutive_passing_measures(measures), 1)

    def test_counts_backwards_from_most_recent(self):
        """An older passing run does not count once a recent one has failed."""
        measures = [
            SRBAIMeasure(NOW, SRBAI_THRESHOLD - 1.0),
            SRBAIMeasure(NOW - timedelta(days=14), SRBAI_THRESHOLD + 1.0),
            SRBAIMeasure(NOW - timedelta(days=28), SRBAI_THRESHOLD + 1.0),
        ]
        self.assertEqual(consecutive_passing_measures(measures), 0)

    def test_ordering_of_input_does_not_matter(self):
        shuffled = list(reversed(passing_measures(2)))
        self.assertEqual(consecutive_passing_measures(shuffled), 2)

    def test_exactly_at_threshold_passes(self):
        self.assertTrue(SRBAIMeasure(NOW, SRBAI_THRESHOLD).passing)
        self.assertFalse(SRBAIMeasure(NOW, SRBAI_THRESHOLD - 0.01).passing)


class TestCompletionCriterion(unittest.TestCase):
    def test_suppressed_occurrences_are_excluded_from_the_denominator(self):
        """The load-bearing test.

        Ten prompted days at 50%, plus ninety suppressed days all completed.
        Counting everything gives ~95% and graduates the habit on the strength
        of us having stopped asking. Counting probe-eligible days gives 50%.
        """
        prompted = [occ(d, completed=(d % 2 == 0)) for d in range(10)]
        suppressed = [
            occ(d, completed=True, policy=PromptPolicy.SUPPRESS) for d in range(10, 30)
        ]
        rate, n = trailing_completion_rate(prompted + suppressed, now=NOW)
        self.assertEqual(n, 10)
        self.assertAlmostEqual(rate, 0.5)

    def test_probe_days_are_included(self):
        """A probe is a withheld prompt, not an absent one — it counts."""
        occs = [occ(d, completed=True, policy=PromptPolicy.PROBE) for d in range(5)]
        rate, n = trailing_completion_rate(occs, now=NOW)
        self.assertEqual(n, 5)
        self.assertAlmostEqual(rate, 1.0)

    def test_skips_and_rest_days_are_excluded_from_both_sides(self):
        """A user who told us they were not doing it has not failed."""
        occs = [occ(d, completed=True) for d in range(8)]
        occs.append(occ(8, completed=False, outcome=Outcome.SKIPPED))
        occs.append(occ(9, completed=False, outcome=Outcome.REST))
        rate, n = trailing_completion_rate(occs, now=NOW)
        self.assertEqual(n, 8)
        self.assertAlmostEqual(rate, 1.0)

    def test_occurrences_outside_the_window_are_ignored(self):
        recent = [occ(d, completed=True) for d in range(5)]
        ancient = [occ(d, completed=False) for d in range(40, 60)]
        rate, n = trailing_completion_rate(recent + ancient, now=NOW)
        self.assertEqual(n, 5)
        self.assertAlmostEqual(rate, 1.0)

    def test_future_occurrences_are_ignored(self):
        future = Occurrence(
            id="future",
            habit_id="h1",
            scheduled_local=NOW + timedelta(days=1),
            window_start=NOW + timedelta(days=1),
            window_end=NOW + timedelta(days=1, hours=1),
            prompt_policy=PromptPolicy.PROMPT,
        )
        rate, n = trailing_completion_rate([occ(1), future], now=NOW)
        self.assertEqual(n, 1)

    def test_no_eligible_occurrences_is_none_not_zero(self):
        """Zero would read as total failure on a habit with no data."""
        rate, n = trailing_completion_rate([], now=NOW)
        self.assertIsNone(rate)
        self.assertEqual(n, 0)


class TestGraduationCheck(unittest.TestCase):
    def _occs(self, rate: float = 1.0, days: int = 20):
        completed = int(days * rate)
        return [occ(d, completed=(d < completed)) for d in range(days)]

    def test_all_three_criteria_met(self):
        result = check_graduation(
            **criteria(make_habit()), measures=passing_measures(2),
            occurrences=self._occs(), now=NOW
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.reasons, ())

    def test_one_passing_measure_is_not_enough(self):
        result = check_graduation(
            **criteria(make_habit()), measures=passing_measures(1),
            occurrences=self._occs(), now=NOW,
        )
        self.assertFalse(result.eligible)
        self.assertFalse(result.srbai_met)
        self.assertTrue(result.fade_met)
        self.assertTrue(result.completion_met)

    def test_still_prompted_blocks_graduation(self):
        """A habit that still needs a notification is not a habit."""
        result = check_graduation(
            **criteria(make_habit(fade_level=FadeLevel.L3)),
            measures=passing_measures(2), occurrences=self._occs(), now=NOW,
        )
        self.assertFalse(result.eligible)
        self.assertFalse(result.fade_met)
        self.assertIn("still prompted at L3", result.reasons)

    def test_completion_below_floor_blocks_graduation(self):
        result = check_graduation(
            **criteria(make_habit()), measures=passing_measures(2),
            occurrences=self._occs(rate=0.5), now=NOW,
        )
        self.assertFalse(result.eligible)
        self.assertFalse(result.completion_met)

    def test_completion_exactly_at_floor_passes(self):
        occs = [occ(d, completed=(d < 8)) for d in range(10)]
        result = check_graduation(
            **criteria(make_habit()), measures=passing_measures(2),
            occurrences=occs, now=NOW,
        )
        assert result.completion_rate is not None
        self.assertAlmostEqual(result.completion_rate, COMPLETION_FLOOR)
        self.assertTrue(result.completion_met)
        self.assertTrue(result.eligible)

    def test_lapsed_habit_never_graduates(self):
        for state in (HabitState.LAPSED_1, HabitState.LAPSED_2,
                      HabitState.DORMANT, HabitState.PAUSED):
            result = check_graduation(
                **criteria(make_habit(state=state)),
                measures=passing_measures(2), occurrences=self._occs(), now=NOW,
            )
            self.assertFalse(result.eligible, state)

    def test_already_graduated_is_not_re_eligible(self):
        result = check_graduation(
            **criteria(make_habit(state=HabitState.GRADUATED)),
            measures=passing_measures(2), occurrences=self._occs(), now=NOW,
        )
        self.assertFalse(result.eligible)

    def test_every_failing_criterion_is_reported(self):
        """The progress surface needs all of them, not just the first."""
        result = check_graduation(
            **criteria(make_habit(fade_level=FadeLevel.L2)),
            measures=passing_measures(0), occurrences=self._occs(rate=0.3), now=NOW,
        )
        self.assertEqual(len(result.reasons), 3)


class TestScheduling(unittest.TestCase):
    def test_first_measure_is_two_weeks_after_creation(self):
        created = datetime(2026, 6, 1, tzinfo=TZ)
        self.assertEqual(
            next_measure_due(None, created_at=created),
            created + timedelta(days=14),
        )

    def test_subsequent_measures_are_biweekly(self):
        last = datetime(2026, 6, 15, tzinfo=TZ)
        self.assertEqual(
            next_measure_due(last, created_at=datetime(2026, 6, 1, tzinfo=TZ)),
            last + timedelta(days=14),
        )

    def test_maintenance_checks_at_30_and_90_days(self):
        graduated = datetime(2026, 6, 1, tzinfo=TZ)
        checks = maintenance_check_dates(graduated)
        self.assertEqual(checks[0], graduated + timedelta(days=30))
        self.assertEqual(checks[1], graduated + timedelta(days=90))
        self.assertEqual(len(checks), 2, "one question, twice, then silence")


class TestGraduationMessage(unittest.TestCase):
    def test_contains_no_metrics(self):
        """§9.3 and the failure-layer tone rules: no streaks, scores or
        percentages in the moments that matter."""
        msg = graduation_message(weeks=14, unprompted_days=30)
        for banned in ("%", "streak", "score", "rank"):
            self.assertNotIn(banned, msg.lower())

    def test_does_not_upsell(self):
        msg = graduation_message(weeks=14, unprompted_days=30).lower()
        for banned in ("upgrade", "premium", "next habit", "start another"):
            self.assertNotIn(banned, msg)

    def test_says_we_will_stop(self):
        msg = graduation_message(weeks=14, unprompted_days=30)
        self.assertIn("stop bringing it up", msg)


if __name__ == "__main__":
    unittest.main()
