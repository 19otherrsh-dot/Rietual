"""
Unit tests for the Failure Layer state machine.

Tests every transition in SPEC-failure-layer §2.1.
Verifies D1: lapsed_1 produces push_side_trigger=False.
No database dependency — pure function tests.
"""
from __future__ import annotations

import pytest

from src.failure_layer.state_machine import (
    HabitEvent,
    HabitStateEnum,
    TransitionResult,
    transition,
)


class TestFormingTransitions:
    def test_miss_goes_to_lapsed_1(self):
        result = transition(HabitStateEnum.FORMING, HabitEvent.MISS)
        assert result.new_state == HabitStateEnum.LAPSED_1

    def test_d1_no_push_on_lapsed_1(self):
        """D1: lapsed_1 MUST NOT trigger a push side effect."""
        result = transition(HabitStateEnum.FORMING, HabitEvent.MISS)
        assert result.push_side_trigger is False, (
            "D1 violated: lapsed_1 transition must have push_side_trigger=False. "
            "The push-side trigger for a first miss was explicitly removed in DECISIONS-v1 D1."
        )

    def test_d1_no_recovery_break_on_first_miss(self):
        """D1: no recovery break pushed at lapsed_1 — pull-initiated only."""
        result = transition(HabitStateEnum.FORMING, HabitEvent.MISS)
        assert result.recovery_break is False

    def test_srbai_threshold_goes_to_established(self):
        result = transition(HabitStateEnum.FORMING, HabitEvent.SRBAI_THRESHOLD_MET)
        assert result.new_state == HabitStateEnum.ESTABLISHED

    def test_pause_goes_to_paused(self):
        result = transition(HabitStateEnum.FORMING, HabitEvent.PAUSE)
        assert result.new_state == HabitStateEnum.PAUSED


class TestLapsed1Transitions:
    def test_completion_recovers_to_forming(self):
        result = transition(HabitStateEnum.LAPSED_1, HabitEvent.COMPLETION)
        assert result.new_state == HabitStateEnum.FORMING
        assert result.push_side_trigger is False

    def test_second_miss_goes_to_lapsed_2(self):
        result = transition(HabitStateEnum.LAPSED_1, HabitEvent.MISS)
        assert result.new_state == HabitStateEnum.LAPSED_2

    def test_lapsed_2_makes_a_recovery_break_available_but_never_pushes_it(self):
        """Second miss makes a recovery break available — in-app only.

        This test previously asserted `push_side_trigger is True`, which
        contradicted SPEC-failure-layer §3.1:

            "Never as a push notification. Recovery content is encountered
             in-app, on next open. A push that says 'you missed your habit'
             is the shame vector this entire feature exists to prevent."

        The no-push rule applies at *every* depth and predates D1 — D1 removed
        the lapsed_1 surface altogether, it did not create the push exception
        at lapsed_2. The only push permitted after a miss is a neutral,
        non-referential re-engagement at the next scheduled occurrence
        ("Tomorrow: [habit], [time]"), which the prompt scheduler owns.
        """
        result = transition(HabitStateEnum.LAPSED_1, HabitEvent.MISS)
        assert result.recovery_break is True
        assert result.push_side_trigger is False

    def test_no_transition_anywhere_sets_a_push_side_trigger(self):
        """Belt and braces: nothing in this module may push recovery content."""
        cases = [
            (HabitStateEnum.FORMING, HabitEvent.MISS),
            (HabitStateEnum.LAPSED_1, HabitEvent.MISS),
            (HabitStateEnum.LAPSED_1, HabitEvent.COMPLETION),
            (HabitStateEnum.LAPSED_2, HabitEvent.MISS),
            (HabitStateEnum.LAPSED_2, HabitEvent.COMPLETION),
            (HabitStateEnum.LAPSED_2, HabitEvent.DORMANCY_THRESHOLD),
            (HabitStateEnum.DORMANT, HabitEvent.COMPLETION),
            (HabitStateEnum.ESTABLISHED, HabitEvent.MISS),
        ]
        for state, event in cases:
            assert transition(state, event).push_side_trigger is False, (
                f"{state.value} + {event.value} would push recovery content"
            )


class TestLapsed2Transitions:
    def test_completion_recovers_to_forming(self):
        result = transition(HabitStateEnum.LAPSED_2, HabitEvent.COMPLETION)
        assert result.new_state == HabitStateEnum.FORMING

    def test_4th_miss_goes_to_dormant(self):
        result = transition(HabitStateEnum.LAPSED_2, HabitEvent.MISS, consecutive_misses=4)
        assert result.new_state == HabitStateEnum.DORMANT

    def test_3rd_miss_stays_lapsed_2(self):
        result = transition(HabitStateEnum.LAPSED_2, HabitEvent.MISS, consecutive_misses=3)
        assert result.new_state == HabitStateEnum.LAPSED_2

    def test_dormancy_threshold_goes_to_dormant(self):
        result = transition(HabitStateEnum.LAPSED_2, HabitEvent.DORMANCY_THRESHOLD)
        assert result.new_state == HabitStateEnum.DORMANT


class TestDormantTransitions:
    def test_completion_returns_to_forming_with_recovery_break(self):
        result = transition(HabitStateEnum.DORMANT, HabitEvent.COMPLETION)
        assert result.new_state == HabitStateEnum.FORMING
        assert result.recovery_break is True  # dormant_return break

    def test_timeout_goes_to_retired(self):
        result = transition(HabitStateEnum.DORMANT, HabitEvent.DORMANT_TIMEOUT)
        assert result.new_state == HabitStateEnum.RETIRED


class TestPausedTransitions:
    def test_resume_goes_to_forming(self):
        result = transition(HabitStateEnum.PAUSED, HabitEvent.RESUME)
        assert result.new_state == HabitStateEnum.FORMING

    def test_miss_while_paused_raises(self):
        """Paused habits must not receive miss events (§2.1 — paused is load-bearing)."""
        with pytest.raises(ValueError, match="paused"):
            transition(HabitStateEnum.PAUSED, HabitEvent.MISS)

    def test_recovery_break_not_triggered_while_paused(self):
        """A user in transition mode must never receive lapse messages."""
        result = transition(HabitStateEnum.PAUSED, HabitEvent.RESUME)
        assert result.recovery_break is False


class TestEstablishedTransitions:
    def test_graduation_criteria_met(self):
        result = transition(HabitStateEnum.ESTABLISHED, HabitEvent.GRADUATION_CRITERIA_MET)
        assert result.new_state == HabitStateEnum.GRADUATED

    def test_miss_from_established_goes_to_lapsed_1(self):
        result = transition(HabitStateEnum.ESTABLISHED, HabitEvent.MISS)
        assert result.new_state == HabitStateEnum.LAPSED_1
        assert result.push_side_trigger is False  # D1 applies to established too


class TestGraduatedTransitions:
    def test_decay_detected_returns_to_forming(self):
        result = transition(HabitStateEnum.GRADUATED, HabitEvent.MISS)
        assert result.new_state == HabitStateEnum.FORMING
        assert result.push_side_trigger is False


class TestD11Invariant:
    """D11: Cue-stability feedback must never appear in the recovery break surface."""

    def test_lapsed_2_transition_note_does_not_mention_stability(self):
        """Recovery break note must not contain stability-related content."""
        result = transition(HabitStateEnum.LAPSED_1, HabitEvent.MISS)
        note_lower = result.note.lower()
        for forbidden in ["stability", "cue", "unstable", "variable", "anchor score"]:
            assert forbidden not in note_lower, (
                f"D11 violated: recovery break transition note contains '{forbidden}'. "
                "Cue-stability must never appear in the recovery surface."
            )
