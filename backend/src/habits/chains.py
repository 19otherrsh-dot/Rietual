"""
Chain assembly — Habit Engine §7.

Chains are implicit in the schema: the habits sharing an anchor, ordered by
`Habit.chain_position`. This module turns those rows into the domain core's
`Chain` so the rules — head-only prompting, the cap of three, the
anchor-stability gate — have exactly one implementation.

Nothing here decides anything. If you find yourself adding a condition to this
file, it probably belongs in `ritual.engine.chains`.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from ritual.engine.chains import Chain as CoreChain
from ritual.engine.chains import prompt_target
from ritual.engine.models import FadeLevel
from ritual.engine.models import Habit as CoreHabit
from ritual.engine.models import HabitState


def _to_core_habit(row) -> CoreHabit:
    """Map an ORM habit onto the core dataclass.

    Only the fields the chain rules read are meaningful; the rest are filled
    from the row so the dataclass is valid rather than left half-built.
    """
    return CoreHabit(
        id=str(row.id),
        user_id=str(row.user_id),
        title=row.title,
        full_version=row.full_version,
        micro_version=row.micro_version,
        anchor_id=str(row.anchor_id) if row.anchor_id else "",
        timezone="UTC",
        state=HabitState(row.state),
        fade_level=FadeLevel(row.fade_level),
    )


def build_chain(anchor_id, habit_rows: Sequence) -> tuple[CoreChain, dict]:
    """Assemble the chain on one anchor.

    Habits with a null `chain_position` are not chain members — a solitary
    habit on an anchor is not a one-link stack, and treating it as one would
    subject it to the head-only rule for no reason.

    Returns (chain, habits_by_id) ready for the core's predicates.
    """
    members = sorted(
        (h for h in habit_rows if h.chain_position is not None),
        key=lambda h: h.chain_position,
    )
    chain = CoreChain(
        id=f"chain:{anchor_id}",
        anchor_id=str(anchor_id),
        habit_ids=[str(h.id) for h in members],
    )
    return chain, {str(h.id): _to_core_habit(h) for h in members}


def prompted_habit_id(anchor_id, habit_rows: Sequence) -> str | None:
    """The one habit on this anchor that may carry a prompt, if any."""
    chain, habits = build_chain(anchor_id, habit_rows)
    if not chain.habit_ids:
        return None
    return prompt_target(chain, habits)


def suppressed_habit_ids(anchor_id, habit_rows: Iterable) -> set[str]:
    """Chain members that must NOT be prompted.

    Everything in the chain except the current prompt target. Note this returns
    the tail even when the head is silent (graduated, paused, faded out): in
    that case the whole chain is silent, which is §7's intent — the stack has
    become one behavioural unit and prompting link two would break it back
    apart.
    """
    rows = list(habit_rows)
    chain, habits = build_chain(anchor_id, rows)
    if not chain.habit_ids:
        return set()
    target = prompt_target(chain, habits)
    return {hid for hid in chain.habit_ids if hid != target}
