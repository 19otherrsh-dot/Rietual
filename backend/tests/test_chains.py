"""Habit stacking — SPEC-habit-engine §7.

The head-only prompting rule gets the most tests because breaking it is silent:
everything still works, the user just gets three notifications instead of one
and no stacking at all.
"""

from __future__ import annotations

import unittest

from ritual.engine.chains import (
    MAX_CHAIN_LENGTH,
    Chain,
    ChainError,
    add_habit,
    can_add,
    chain_position,
    cue_for,
    prompt_target,
    remove_habit,
    reorder,
    should_prompt,
)
from ritual.engine.models import (
    FadeLevel,
    Habit,
    HabitState,
    Stability,
    StabilityBasis,
    StabilityReport,
)


def report(verdict: Stability) -> StabilityReport:
    return StabilityReport(
        verdict=verdict,
        basis=StabilityBasis.OBSERVED,
        weakest_dimension="temporal",
    )


STABLE = report(Stability.STABLE)
VARIABLE = report(Stability.VARIABLE)
UNSTABLE = report(Stability.UNSTABLE)


def habit(hid: str, title: str, **kw) -> Habit:
    base = dict(
        id=hid,
        user_id="u1",
        title=title,
        full_version=title,
        micro_version=f"tiny {title}",
        anchor_id="coffee",
        timezone="Europe/London",
        state=HabitState.FORMING,
        fade_level=FadeLevel.L0,
    )
    base.update(kw)
    return Habit(**base)


def stack(*habits: Habit) -> tuple[Chain, dict[str, Habit]]:
    chain = Chain(id="c1", anchor_id="coffee", habit_ids=[h.id for h in habits])
    return chain, {h.id: h for h in habits}


WATER = habit("h1", "Water")
STRETCH = habit("h2", "Stretch")
INTENTION = habit("h3", "Intention")


class TestHeadOnlyPrompting(unittest.TestCase):
    def test_only_the_head_is_prompted(self):
        chain, habits = stack(WATER, STRETCH, INTENTION)
        self.assertEqual(prompt_target(chain, habits), "h1")
        self.assertTrue(should_prompt("h1", chain, habits))
        self.assertFalse(should_prompt("h2", chain, habits))
        self.assertFalse(should_prompt("h3", chain, habits))

    def test_graduated_head_silences_the_whole_chain(self):
        """The chain is by then a single behavioural unit — the intended
        outcome. Prompting must not fall through to link two."""
        chain, habits = stack(
            habit("h1", "Water", state=HabitState.GRADUATED, fade_level=FadeLevel.L4),
            STRETCH,
            INTENTION,
        )
        self.assertIsNone(prompt_target(chain, habits))
        for hid in ("h1", "h2", "h3"):
            self.assertFalse(should_prompt(hid, chain, habits))

    def test_head_at_l4_silences_the_chain(self):
        chain, habits = stack(habit("h1", "Water", fade_level=FadeLevel.L4), STRETCH)
        self.assertIsNone(prompt_target(chain, habits))

    def test_paused_head_silences_the_chain(self):
        chain, habits = stack(habit("h1", "Water", state=HabitState.PAUSED), STRETCH)
        self.assertIsNone(prompt_target(chain, habits))

    def test_lapsed_head_does_not_promote_link_two(self):
        """A lapsed head keeps its own recovery handling. Promoting the next
        link would quietly split the stack into independent habits at the
        worst possible moment."""
        for state in (HabitState.LAPSED_1, HabitState.LAPSED_2, HabitState.DORMANT):
            chain, habits = stack(habit("h1", "Water", state=state), STRETCH)
            self.assertEqual(prompt_target(chain, habits), "h1", state)
            self.assertFalse(should_prompt("h2", chain, habits), state)

    def test_habit_outside_a_chain_is_unconstrained(self):
        chain, habits = stack(WATER, STRETCH)
        self.assertTrue(should_prompt("other", chain, habits))
        self.assertTrue(should_prompt("h2", None, habits))


class TestChainLimits(unittest.TestCase):
    def test_cap_is_three(self):
        chain, _ = stack(WATER, STRETCH, INTENTION)
        self.assertTrue(chain.is_full)
        allowed, reason = can_add(chain, STABLE)
        self.assertFalse(allowed)
        self.assertIn("full", reason.lower())

    def test_constructing_an_oversized_chain_is_refused(self):
        with self.assertRaises(ChainError):
            Chain(
                id="c1",
                anchor_id="coffee",
                habit_ids=["h1", "h2", "h3", "h4"],
            )

    def test_duplicate_membership_is_refused(self):
        with self.assertRaises(ChainError):
            Chain(id="c1", anchor_id="coffee", habit_ids=["h1", "h1"])

    def test_max_is_three(self):
        self.assertEqual(MAX_CHAIN_LENGTH, 3)


class TestAnchorStabilityGate(unittest.TestCase):
    def test_stable_anchor_allows_stacking(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        self.assertTrue(can_add(chain, STABLE)[0])

    def test_variable_anchor_allows_stacking(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        self.assertTrue(can_add(chain, VARIABLE)[0])

    def test_unstable_anchor_refuses_stacking(self):
        """Building a three-link chain on an unstable cue is a designed
        failure, so we refuse rather than warn."""
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        allowed, reason = can_add(chain, UNSTABLE)
        self.assertFalse(allowed)
        self.assertIn("moves around too much", reason)

    def test_unscored_anchor_refuses_stacking(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        self.assertFalse(can_add(chain, None)[0])
        self.assertFalse(can_add(chain, report(Stability.UNKNOWN))[0])

    def test_refusal_explains_itself(self):
        """A reason the UI can render beats a disabled button."""
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        for stability in (UNSTABLE, None):
            _, reason = can_add(chain, stability)
            self.assertTrue(reason and len(reason) > 20)


class TestMutation(unittest.TestCase):
    def test_add_appends_to_the_tail(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        updated = add_habit(chain, "h2", STABLE)
        self.assertEqual(updated.habit_ids, ["h1", "h2"])
        self.assertEqual(updated.head, "h1")

    def test_add_is_immutable(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        add_habit(chain, "h2", STABLE)
        self.assertEqual(chain.habit_ids, ["h1"], "original mutated")

    def test_add_refuses_a_duplicate(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        with self.assertRaises(ChainError):
            add_habit(chain, "h1", STABLE)

    def test_add_refuses_on_unstable_anchor(self):
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["h1"])
        with self.assertRaises(ChainError):
            add_habit(chain, "h2", UNSTABLE)

    def test_removing_the_head_promotes_the_next_link(self):
        """A deliberate user action, unlike graduation."""
        chain, _ = stack(WATER, STRETCH, INTENTION)
        updated = remove_habit(chain, "h1")
        self.assertEqual(updated.head, "h2")

    def test_remove_rejects_a_non_member(self):
        chain, _ = stack(WATER, STRETCH)
        with self.assertRaises(ChainError):
            remove_habit(chain, "nope")

    def test_reorder_must_preserve_membership(self):
        chain, _ = stack(WATER, STRETCH, INTENTION)
        self.assertEqual(reorder(chain, ["h3", "h1", "h2"]).head, "h3")
        with self.assertRaises(ChainError):
            reorder(chain, ["h1", "h2"])


class TestCueRendering(unittest.TestCase):
    def test_head_is_cued_by_the_anchor(self):
        chain, habits = stack(WATER, STRETCH, INTENTION)
        self.assertEqual(cue_for(chain, "h1", habits), "After coffee")

    def test_links_are_cued_by_the_previous_habit(self):
        chain, habits = stack(WATER, STRETCH, INTENTION)
        self.assertEqual(cue_for(chain, "h2", habits), "After Water")
        self.assertEqual(cue_for(chain, "h3", habits), "After Stretch")

    def test_non_member_has_no_cue(self):
        chain, habits = stack(WATER, STRETCH)
        self.assertIsNone(cue_for(chain, "nope", habits))

    def test_position_lookup(self):
        chain, _ = stack(WATER, STRETCH, INTENTION)
        self.assertEqual(chain_position(chain, "h1"), 0)
        self.assertEqual(chain_position(chain, "h3"), 2)
        self.assertIsNone(chain_position(chain, "nope"))


class TestEmptyChain(unittest.TestCase):
    def test_empty_chain_prompts_nothing(self):
        chain = Chain(id="c1", anchor_id="coffee")
        self.assertIsNone(chain.head)
        self.assertIsNone(prompt_target(chain, {}))

    def test_missing_head_habit_prompts_nothing(self):
        """Defensive: a dangling reference must not crash the scheduler."""
        chain = Chain(id="c1", anchor_id="coffee", habit_ids=["ghost"])
        self.assertIsNone(prompt_target(chain, {}))


if __name__ == "__main__":
    unittest.main()
