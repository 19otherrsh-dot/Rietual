"""Engine correctness tests.

These map one-to-one onto the launch gates in PLAN-phase1-v1 §7 that concern
the habit engine. Where a test looks pedantic, the spec section it cites
explains why it is not.

Run:  python -m unittest discover -s backend/tests -t .
"""

from __future__ import annotations

import pathlib
import random
import unittest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ritual.engine import (
    Anchor,
    AnchorClass,
    FadeLevel,
    Habit,
    HabitState,
    Occurrence,
    Outcome,
    PromptPolicy,
    Stability,
    StabilityBasis,
    advance,
    assign_prompt_policies,
    circular_mad_minutes,
    circular_mean_time,
    generate_occurrences,
    is_unprompted,
    miss_detection_due_at,
    regress,
    resolve_local,
    resolve_outcome,
    score_anchor,
    should_advance,
    unprompted_rate,
    window_for,
)
from ritual.engine.fading import counts_toward_lapse
from ritual.engine.scheduling import (
    detect_timezone_change,
    stability_scoring_paused_until,
)
from ritual.engine.models import StabilityReport

LONDON = ZoneInfo("Europe/London")
NEW_YORK = ZoneInfo("America/New_York")


def make_habit(**kw) -> Habit:
    base = dict(
        id="h1",
        user_id="u1",
        title="Morning stretch",
        full_version="10 minute stretch",
        micro_version="Two shoulder rolls",
        anchor_id="a1",
        timezone="Europe/London",
    )
    base.update(kw)
    return Habit(**base)


def make_anchor(nominal_time="07:00", stability=None) -> Anchor:
    return Anchor(
        id="a1",
        user_id="u1",
        anchor_class=AnchorClass.WAKE,
        label="After I wake up",
        nominal_time=nominal_time,
        stability=stability,
    )


# ---------------------------------------------------------------------------
# Gate: wall-clock scheduling across both DST directions
# ---------------------------------------------------------------------------


class TestDaylightSaving(unittest.TestCase):
    def test_seven_days_across_spring_forward(self):
        """UK clocks go forward 29 March 2026. A 07:00 habit stays at 07:00."""
        occ = generate_occurrences(
            make_habit(), make_anchor("07:00"), date(2026, 3, 26), days=7
        )
        self.assertEqual(len(occ), 7, "no duplicate or missing occurrence")
        for o in occ:
            self.assertEqual(o.scheduled_local.hour, 7)
            self.assertEqual(o.scheduled_local.minute, 0)

        # The wall clock held; the underlying instants shifted by an hour.
        before = occ[0].scheduled_local.utcoffset()
        after = occ[-1].scheduled_local.utcoffset()
        assert before is not None and after is not None
        self.assertEqual(after - before, timedelta(hours=1))

    def test_seven_days_across_fall_back(self):
        """UK clocks go back 25 October 2026."""
        occ = generate_occurrences(
            make_habit(), make_anchor("07:00"), date(2026, 10, 22), days=7
        )
        self.assertEqual(len(occ), 7)
        for o in occ:
            self.assertEqual(o.scheduled_local.hour, 7)
        before = occ[0].scheduled_local.utcoffset()
        after = occ[-1].scheduled_local.utcoffset()
        assert before is not None and after is not None
        self.assertEqual(after - before, timedelta(hours=-1))

    def test_nonexistent_local_time_shifts_forward(self):
        """01:30 does not exist on 29 March 2026 in London.

        We shift forward by the gap rather than dropping the occurrence: a
        habit that silently vanishes for a day is worse than one that fires an
        hour late once a year.
        """
        resolved = resolve_local(datetime(2026, 3, 29, 1, 30), LONDON)
        self.assertEqual((resolved.hour, resolved.minute), (2, 30))

    def test_nonexistent_local_time_us(self):
        """02:30 does not exist on 8 March 2026 in New York."""
        resolved = resolve_local(datetime(2026, 3, 8, 2, 30), NEW_YORK)
        self.assertEqual((resolved.hour, resolved.minute), (3, 30))

    def test_ambiguous_local_time_takes_first_instant(self):
        """01:30 happens twice on 25 October 2026 in London.

        We take the first (fold=0) deterministically so the habit fires once.
        """
        resolved = resolve_local(datetime(2026, 10, 25, 1, 30), LONDON)
        self.assertEqual((resolved.hour, resolved.minute), (1, 30))
        self.assertEqual(resolved.fold, 0)
        self.assertEqual(resolved.utcoffset(), timedelta(hours=1))  # still BST

    def test_ambiguous_day_yields_exactly_one_occurrence(self):
        occ = generate_occurrences(
            make_habit(), make_anchor("01:30"), date(2026, 10, 25), days=1
        )
        self.assertEqual(len(occ), 1)

    def test_ordinary_time_unaffected(self):
        resolved = resolve_local(datetime(2026, 6, 1, 7, 0), LONDON)
        self.assertEqual((resolved.hour, resolved.minute), (7, 0))
        self.assertEqual(resolved.utcoffset(), timedelta(hours=1))


# ---------------------------------------------------------------------------
# Gate: timezone change — no 4am prompts on arrival
# ---------------------------------------------------------------------------


class TestTimezoneChange(unittest.TestCase):
    def test_wall_clock_preserved_after_flight(self):
        home = generate_occurrences(
            make_habit(timezone="America/New_York"),
            make_anchor("07:00"),
            date(2026, 6, 1),
            days=1,
        )[0]
        away = generate_occurrences(
            make_habit(timezone="Europe/London"),
            make_anchor("07:00"),
            date(2026, 6, 1),
            days=1,
        )[0]
        self.assertEqual(home.scheduled_local.hour, 7)
        self.assertEqual(away.scheduled_local.hour, 7)
        # Same wall clock, different instants — which is the point.
        self.assertNotEqual(
            home.scheduled_local.astimezone(ZoneInfo("UTC")),
            away.scheduled_local.astimezone(ZoneInfo("UTC")),
        )

    def test_large_shift_pauses_stability_scoring(self):
        at = datetime(2026, 6, 1, 12, 0)
        delta = detect_timezone_change("America/New_York", "Europe/London", at)
        self.assertEqual(delta, timedelta(hours=5))
        until = stability_scoring_paused_until(
            delta, datetime(2026, 6, 1, 12, 0, tzinfo=LONDON)
        )
        self.assertIsNotNone(until)
        self.assertEqual(until - datetime(2026, 6, 1, 12, 0, tzinfo=LONDON), timedelta(days=3))

    def test_small_shift_does_not_pause(self):
        at = datetime(2026, 6, 1, 12, 0)
        delta = detect_timezone_change("Europe/London", "Europe/Lisbon", at)
        self.assertIsNone(stability_scoring_paused_until(delta, datetime.now(LONDON)))

    def test_no_change_returns_none(self):
        self.assertIsNone(
            detect_timezone_change("Europe/London", "Europe/London", datetime(2026, 6, 1))
        )


# ---------------------------------------------------------------------------
# Gate: circular statistics, midnight-spanning
# ---------------------------------------------------------------------------


class TestCircularStatistics(unittest.TestCase):
    def test_mean_spans_midnight(self):
        """23:50 and 00:10 average to midnight, not to noon."""
        mean = circular_mean_time([time(23, 50), time(0, 10)])
        self.assertIn((mean.hour, mean.minute), [(0, 0), (23, 59)])

    def test_naive_mean_would_have_been_wrong(self):
        """Guards the specific bug: a naive mean returns 12:00 here."""
        mean = circular_mean_time([time(23, 50), time(0, 10)])
        self.assertNotEqual(mean.hour, 12)

    def test_mad_spans_midnight(self):
        mad = circular_mad_minutes([time(23, 50), time(0, 10)])
        self.assertAlmostEqual(mad, 10.0, places=1)

    def test_tight_cluster_is_stable(self):
        times = [time(7, m) for m in (0, 5, 2, 8, 3, 6, 1, 4, 7, 2, 5, 3, 6, 4)]
        verdict, provisional = _temporal(times)
        self.assertIs(verdict, Stability.STABLE)
        self.assertFalse(provisional)

    def test_wide_spread_is_unstable(self):
        times = [time(6, 40), time(11, 15), time(7, 30), time(10, 45),
                 time(6, 50), time(11, 0), time(8, 15), time(10, 30),
                 time(7, 0), time(11, 30), time(6, 45), time(10, 0),
                 time(9, 30), time(6, 30)]
        verdict, _ = _temporal(times)
        self.assertIs(verdict, Stability.UNSTABLE)

    def test_median_resists_a_single_outlier(self):
        """One 3am morning in a fortnight of 07:00s must not condemn an anchor."""
        times = [time(7, 0)] * 13 + [time(3, 0)]
        verdict, _ = _temporal(times)
        self.assertIs(verdict, Stability.STABLE)

    def test_too_few_samples_is_unknown(self):
        verdict, provisional = _temporal([time(7, 0)] * 4)
        self.assertIs(verdict, Stability.UNKNOWN)
        self.assertTrue(provisional)


def _temporal(times):
    from ritual.engine.stability import temporal_stability

    return temporal_stability(times)


# ---------------------------------------------------------------------------
# Gate: stability basis is never implied as observed
# ---------------------------------------------------------------------------


class TestStabilityReport(unittest.TestCase):
    def test_cold_start_falls_back_to_class_prior(self):
        report = score_anchor(AnchorClass.WAKE)
        self.assertIs(report.basis, StabilityBasis.PRIOR)
        self.assertIs(report.verdict, Stability.STABLE)
        self.assertTrue(report.provisional)

    def test_work_end_prior_is_variable(self):
        """The single most over-trusted anchor users pick (§3.4)."""
        self.assertIs(score_anchor(AnchorClass.WORK_END).verdict, Stability.VARIABLE)

    def test_calendar_used_when_no_observations(self):
        report = score_anchor(AnchorClass.CUSTOM, calendar_same_shape_share=0.9)
        self.assertIs(report.basis, StabilityBasis.CALENDAR)
        self.assertIs(report.verdict, Stability.STABLE)

    def test_reports_weakest_dimension_not_an_average(self):
        """Stable temporally, unstable locationally -> the verdict is unstable."""
        report = score_anchor(
            AnchorClass.WAKE,
            completion_times=[time(7, m % 10) for m in range(14)],
            modal_cluster_share=0.2,
            calendar_same_shape_share=0.95,
        )
        self.assertIs(report.basis, StabilityBasis.OBSERVED)
        self.assertIs(report.verdict, Stability.UNSTABLE)
        self.assertEqual(report.weakest_dimension, "locational")

    def test_absent_dimension_is_not_a_verdict(self):
        """Denied location permission must not read as instability."""
        report = score_anchor(
            AnchorClass.WAKE,
            completion_times=[time(7, m % 10) for m in range(14)],
            modal_cluster_share=None,
        )
        self.assertIs(report.verdict, Stability.STABLE)
        self.assertEqual(report.weakest_dimension, "temporal")


class TestStabilityBoundaries(unittest.TestCase):
    """Exact-threshold behaviour, per the SPEC-habit-engine §3.1 table.

    Stable "< 30", Variable "30–75", Unstable "> 75" — so 30 and 75 are both
    variable. Locational stable is "> 0.75" and variable "0.5–0.75", so 0.75 is
    variable. These landed the wrong side of the line in the pre-merge
    implementation, and the temporal one additionally needed the MAD rounded:
    a genuine 75-minute spread computes to 75.000000000000014 through the
    trigonometric round trip.
    """

    def test_mad_of_exactly_75_is_variable(self):
        times = [time(6, 45)] * 7 + [time(9, 15)] * 7  # ±75 min about 08:00
        verdict, _ = _temporal(times)
        self.assertIs(verdict, Stability.VARIABLE)

    def test_mad_just_over_75_is_unstable(self):
        times = [time(6, 43)] * 7 + [time(9, 17)] * 7  # ±77 min
        verdict, _ = _temporal(times)
        self.assertIs(verdict, Stability.UNSTABLE)

    def test_locational_exactly_at_threshold_is_variable(self):
        from ritual.engine.stability import locational_stability

        self.assertIs(locational_stability(0.75), Stability.VARIABLE)
        self.assertIs(locational_stability(0.76), Stability.STABLE)

    def test_calendar_exactly_at_threshold_is_variable(self):
        from ritual.engine.stability import calendar_stability

        self.assertIs(calendar_stability(0.70), Stability.VARIABLE)
        self.assertIs(calendar_stability(0.71), Stability.STABLE)


class TestApplicationAdapter(unittest.TestCase):
    """Guards the merge itself: src/ must agree with the domain core.

    `src.habits.stability` is a thin adapter so the workers and routers keep
    their existing call shape. If it drifts from `ritual.engine.stability`, the
    two implementations we just merged have started separating again.
    """

    def test_adapter_agrees_with_core_on_midnight_spanning_times(self):
        from src.habits.stability import score_temporal

        score = score_temporal([time(23, 50), time(0, 10)] * 7)
        assert score.value is not None
        self.assertEqual(round(score.value), 10)
        self.assertEqual(score.level, "stable")

    def test_adapter_reports_prior_basis_below_minimum_samples(self):
        from src.habits.stability import score_temporal

        score = score_temporal([time(7, 0)] * 4)
        self.assertEqual(score.level, "unscored")
        self.assertEqual(score.basis, "prior")

    def test_adapter_excludes_unscored_from_worst_of(self):
        from src.habits.stability import overall_level, score_temporal

        temporal = score_temporal([time(7, m % 10) for m in range(14)])
        self.assertEqual(overall_level(temporal, None, None), "stable")

    def test_adapter_imports_without_web_or_db_dependencies(self):
        """The adapter must not drag FastAPI or SQLAlchemy into the core's
        test path — that is the property that keeps this suite fast.

        Runs in a subprocess deliberately. Asserting against this process's
        `sys.modules` would pass or fail depending on whether an integration
        module happened to be imported first, which is a test that reports on
        collection order rather than on the code.
        """
        import subprocess
        import sys
        import textwrap

        probe = textwrap.dedent(
            """
            import sys
            import src.habits.stability  # noqa: F401
            forbidden = ("fastapi", "sqlalchemy", "celery", "numpy", "pytz")
            leaked = sorted(m for m in forbidden if m in sys.modules)
            print(",".join(leaked))
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            cwd=str(pathlib.Path(__file__).resolve().parent.parent),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        leaked = result.stdout.strip()
        self.assertEqual(leaked, "", f"adapter pulled in: {leaked}")


# ---------------------------------------------------------------------------
# Windows and quiet hours
# ---------------------------------------------------------------------------


class TestWindows(unittest.TestCase):
    def test_unstable_anchor_gets_a_wider_window(self):
        unstable = StabilityReport(
            verdict=Stability.UNSTABLE,
            basis=StabilityBasis.OBSERVED,
            weakest_dimension="temporal",
        )
        self.assertEqual(window_for(None), timedelta(minutes=90))
        self.assertEqual(window_for(unstable), timedelta(hours=3))

    def test_miss_detection_deferred_out_of_quiet_hours(self):
        """A 21:00 habit closes at 22:30; +2h grace lands at 00:30.

        Detection defers to 07:00 rather than firing overnight.
        """
        occ = generate_occurrences(
            make_habit(), make_anchor("21:00"), date(2026, 6, 1), days=1
        )[0]
        due = miss_detection_due_at(occ)
        self.assertEqual(due.hour, 7)
        self.assertEqual(due.date(), date(2026, 6, 2))

    def test_daytime_miss_detected_same_day(self):
        occ = generate_occurrences(
            make_habit(), make_anchor("12:00"), date(2026, 6, 1), days=1
        )[0]
        due = miss_detection_due_at(occ)
        self.assertEqual(due.date(), date(2026, 6, 1))
        self.assertEqual(due.hour, 15)  # 13:30 close + 2h grace


# ---------------------------------------------------------------------------
# Gate: unprompted attribution uses delivery time
# ---------------------------------------------------------------------------


class TestAttribution(unittest.TestCase):
    def _occ(self, **kw) -> Occurrence:
        base = dict(
            id="o1",
            habit_id="h1",
            scheduled_local=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            window_start=datetime(2026, 6, 1, 5, 30, tzinfo=LONDON),
            window_end=datetime(2026, 6, 1, 8, 30, tzinfo=LONDON),
        )
        base.update(kw)
        return Occurrence(**base)

    def test_no_prompt_means_unprompted(self):
        occ = self._occ(completed_at=datetime(2026, 6, 1, 7, 5, tzinfo=LONDON))
        self.assertTrue(is_unprompted(occ))

    def test_delivered_before_completion_is_prompted(self):
        occ = self._occ(
            prompt_sent_at=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            prompt_delivered_at=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            completed_at=datetime(2026, 6, 1, 7, 5, tzinfo=LONDON),
        )
        self.assertFalse(is_unprompted(occ))

    def test_delayed_delivery_does_not_retroactively_prompt(self):
        """Sent 07:00, phone offline, delivered 09:40, completed 08:15.

        The prompt cannot have caused the completion. Treating it as prompted
        would understate automaticity for users with the least reliable phones.
        """
        occ = self._occ(
            prompt_sent_at=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            prompt_delivered_at=datetime(2026, 6, 1, 9, 40, tzinfo=LONDON),
            completed_at=datetime(2026, 6, 1, 8, 15, tzinfo=LONDON),
        )
        self.assertTrue(is_unprompted(occ))

    def test_incomplete_is_not_unprompted(self):
        self.assertFalse(is_unprompted(self._occ()))

    def test_sent_but_never_delivered_is_unprompted(self):
        """A prompt that never reached the user cannot have caused anything.

        Regression guard. The application layer previously computed
        `prompt_delivered_at or prompt_sent_at`, so an undelivered prompt was
        scored against its send time and the completion came out *prompted* —
        inverting the rule for exactly the users whose phones are least
        reliable, and understating the primary success metric.
        """
        occ = self._occ(
            prompt_sent_at=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            prompt_delivered_at=None,
            completed_at=datetime(2026, 6, 1, 8, 15, tzinfo=LONDON),
        )
        self.assertTrue(is_unprompted(occ))

    def test_application_layer_agrees_with_the_core(self):
        from src.occurrences.service import compute_unprompted

        sent = datetime(2026, 6, 1, 7, 0, tzinfo=LONDON)
        completed = datetime(2026, 6, 1, 8, 15, tzinfo=LONDON)
        delivered_late = datetime(2026, 6, 1, 9, 40, tzinfo=LONDON)
        delivered_early = datetime(2026, 6, 1, 7, 1, tzinfo=LONDON)

        self.assertTrue(compute_unprompted(sent, None, completed))
        self.assertTrue(compute_unprompted(sent, delivered_late, completed))
        self.assertFalse(compute_unprompted(sent, delivered_early, completed))
        self.assertTrue(compute_unprompted(None, None, completed))

    def test_rate_denominator_excludes_suppressed_occurrences(self):
        """Otherwise the metric rises trivially with fading (§6.2)."""
        prompted_done = self._occ(
            prompt_delivered_at=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            completed_at=datetime(2026, 6, 1, 7, 5, tzinfo=LONDON),
        )
        probe_done = self._occ(
            prompt_policy=PromptPolicy.PROBE,
            completed_at=datetime(2026, 6, 1, 7, 5, tzinfo=LONDON),
        )
        suppressed_done = self._occ(
            prompt_policy=PromptPolicy.SUPPRESS,
            completed_at=datetime(2026, 6, 1, 7, 5, tzinfo=LONDON),
        )
        rate = unprompted_rate([prompted_done, probe_done, suppressed_done])
        assert rate is not None
        self.assertAlmostEqual(rate, 0.5)  # suppressed excluded from denominator


# ---------------------------------------------------------------------------
# Gate: probe fences, and probe misses excluded from lapse progression
# ---------------------------------------------------------------------------


class TestProbes(unittest.TestCase):
    def _week(self, habit, start=date(2026, 6, 1)):
        return generate_occurrences(habit, make_anchor("07:00"), start, days=7)

    def _assign(self, habit, week, **kw):
        params = dict(
            now=datetime(2026, 6, 1, 3, 0, tzinfo=LONDON),
            habit_created_at=datetime(2026, 4, 1, 9, 0, tzinfo=LONDON),
            rng=random.Random(7),
        )
        params.update(kw)
        return assign_prompt_policies(habit, week, **params)

    def test_probe_scheduled_for_an_eligible_habit(self):
        habit = make_habit(state=HabitState.FORMING)
        week = self._assign(habit, self._week(habit))
        self.assertEqual(
            sum(1 for o in week if o.prompt_policy is PromptPolicy.PROBE), 1
        )

    def test_no_probe_in_first_week(self):
        habit = make_habit()
        week = self._assign(
            habit,
            self._week(habit),
            habit_created_at=datetime(2026, 5, 28, 9, 0, tzinfo=LONDON),
        )
        self.assertEqual(
            sum(1 for o in week if o.prompt_policy is PromptPolicy.PROBE), 0
        )

    def test_no_probe_while_lapsed(self):
        for state in (HabitState.LAPSED_1, HabitState.LAPSED_2,
                      HabitState.DORMANT, HabitState.PAUSED):
            habit = make_habit(state=state)
            week = self._assign(habit, self._week(habit))
            self.assertEqual(
                sum(1 for o in week if o.prompt_policy is PromptPolicy.PROBE),
                0,
                f"probe scheduled while {state}",
            )

    def test_user_weekly_cap_enforced(self):
        habit = make_habit()
        week = self._assign(habit, self._week(habit), user_probes_this_week=2)
        self.assertEqual(
            sum(1 for o in week if o.prompt_policy is PromptPolicy.PROBE), 0
        )

    def test_avoids_last_weeks_weekday(self):
        habit = make_habit()
        for _ in range(20):  # the choice is random; the constraint is not
            week = self._assign(
                habit,
                self._week(habit),
                last_probe_weekday=0,  # Monday
                rng=random.Random(),
            )
            probes = [o for o in week if o.prompt_policy is PromptPolicy.PROBE]
            for p in probes:
                self.assertNotEqual(p.scheduled_local.weekday(), 0)

    def test_no_probe_at_l4(self):
        """Nothing to withhold once prompting has stopped."""
        habit = make_habit(fade_level=FadeLevel.L4)
        week = self._assign(habit, self._week(habit))
        self.assertEqual(
            sum(1 for o in week if o.prompt_policy is PromptPolicy.PROBE), 0
        )

    def test_probe_miss_is_not_a_lapse(self):
        """We withheld the prompt, so we absorb the miss (§5.3)."""
        probe = Occurrence(
            id="o1",
            habit_id="h1",
            scheduled_local=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            window_start=datetime(2026, 6, 1, 5, 30, tzinfo=LONDON),
            window_end=datetime(2026, 6, 1, 8, 30, tzinfo=LONDON),
            prompt_policy=PromptPolicy.PROBE,
        )
        outcome = resolve_outcome(probe)
        self.assertIs(outcome, Outcome.PROBE_MISS)
        self.assertFalse(counts_toward_lapse(outcome))

    def test_ordinary_miss_does_count(self):
        missed = Occurrence(
            id="o2",
            habit_id="h1",
            scheduled_local=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            window_start=datetime(2026, 6, 1, 5, 30, tzinfo=LONDON),
            window_end=datetime(2026, 6, 1, 8, 30, tzinfo=LONDON),
            prompt_policy=PromptPolicy.PROMPT,
            prompt_delivered_at=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
        )
        self.assertTrue(counts_toward_lapse(resolve_outcome(missed)))


# ---------------------------------------------------------------------------
# Gate: fade ladder movement
# ---------------------------------------------------------------------------


class TestLadder(unittest.TestCase):
    def _completed(self, prompted: bool) -> Occurrence:
        return Occurrence(
            id="o",
            habit_id="h1",
            scheduled_local=datetime(2026, 6, 1, 7, 0, tzinfo=LONDON),
            window_start=datetime(2026, 6, 1, 5, 30, tzinfo=LONDON),
            window_end=datetime(2026, 6, 1, 8, 30, tzinfo=LONDON),
            prompt_delivered_at=(
                datetime(2026, 6, 1, 7, 0, tzinfo=LONDON) if prompted else None
            ),
            completed_at=datetime(2026, 6, 1, 7, 5, tzinfo=LONDON),
        )

    def test_advances_after_three_unprompted(self):
        habit = make_habit()
        self.assertTrue(should_advance(habit, [self._completed(False)] * 3))

    def test_does_not_advance_on_two(self):
        habit = make_habit()
        self.assertFalse(should_advance(habit, [self._completed(False)] * 2))

    def test_prompted_completion_breaks_the_streak(self):
        habit = make_habit()
        recent = [self._completed(False), self._completed(True), self._completed(False)]
        self.assertFalse(should_advance(habit, recent))

    def test_does_not_advance_while_lapsed(self):
        habit = make_habit(state=HabitState.LAPSED_2)
        self.assertFalse(should_advance(habit, [self._completed(False)] * 5))

    def test_regression_is_one_level_and_never_to_l0(self):
        self.assertIs(regress(FadeLevel.L3), FadeLevel.L2)
        self.assertIs(regress(FadeLevel.L1), FadeLevel.L1)
        self.assertIs(regress(FadeLevel.L2), FadeLevel.L1)

    def test_advance_caps_at_l4(self):
        self.assertIs(advance(FadeLevel.L4), FadeLevel.L4)

    def test_prompt_restoration_expires_after_seven_days(self):
        """The one sanctioned way back up the ladder, and it is time-boxed."""
        from ritual.engine.fading import effective_fade_level

        restore_until = datetime(2026, 6, 8, 9, 0, tzinfo=LONDON)
        habit = make_habit(fade_level=FadeLevel.L3, prompt_restore_until=restore_until)

        during = datetime(2026, 6, 5, 9, 0, tzinfo=LONDON)
        after = datetime(2026, 6, 8, 9, 1, tzinfo=LONDON)
        self.assertIs(effective_fade_level(habit, during), FadeLevel.L0)
        self.assertIs(effective_fade_level(habit, after), FadeLevel.L3)


if __name__ == "__main__":
    unittest.main()
