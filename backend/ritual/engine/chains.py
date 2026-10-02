"""Habit stacking — chains.

Implements SPEC-habit-engine-v1 §7.

A chain is an ordered list of habits sharing one anchor:

    After [morning coffee] -> water -> stretch -> intention

The load-bearing rule is that **only the head habit is prompted**. The rest are
cued by the habit before them — that is the entire mechanism of stacking, and
prompting each link separately destroys it: the user stops being cued by
finishing the previous action and starts being cued by their phone, which is
three notifications where there should be one and no stacking at all.

The cap of three is deliberate (§7): longer chains fail as a unit, and a
four-link chain is a common way for someone to lose four habits in one bad
morning rather than one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from .models import (
    FadeLevel,
    Habit,
    HabitState,
    Stability,
    StabilityReport,
)

#: §7. Longer chains fail as a unit.
MAX_CHAIN_LENGTH = 3

#: Anchors a chain may be built on. Building a three-link chain on an unstable
#: cue is a designed failure, so we refuse rather than warn.
CHAINABLE = frozenset({Stability.STABLE, Stability.VARIABLE})


class ChainError(ValueError):
    """Raised when a chain operation would violate §7."""


@dataclass
class Chain:
    """An ordered stack of habits on one anchor.

    ``habit_ids[0]`` is the head — the only member that is ever prompted.
    """

    id: str
    anchor_id: str
    habit_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.habit_ids) > MAX_CHAIN_LENGTH:
            raise ChainError(
                f"chain {self.id} has {len(self.habit_ids)} habits; "
                f"the maximum is {MAX_CHAIN_LENGTH}"
            )
        if len(set(self.habit_ids)) != len(self.habit_ids):
            raise ChainError(f"chain {self.id} contains a duplicate habit")

    @property
    def head(self) -> Optional[str]:
        return self.habit_ids[0] if self.habit_ids else None

    @property
    def tail(self) -> list[str]:
        return self.habit_ids[1:]

    @property
    def is_full(self) -> bool:
        return len(self.habit_ids) >= MAX_CHAIN_LENGTH


def can_add(
    chain: Chain, anchor_stability: Optional[StabilityReport]
) -> tuple[bool, Optional[str]]:
    """Whether another habit may join this chain, and why not if not.

    Returns a reason rather than raising so the caller can render it: "this
    anchor moves too much to stack on" is useful, a disabled button is not.
    """
    if chain.is_full:
        return False, (
            f"This stack is full at {MAX_CHAIN_LENGTH}. Longer stacks tend to "
            "break all at once rather than one at a time."
        )

    if anchor_stability is None or anchor_stability.verdict not in CHAINABLE:
        return False, (
            "This anchor moves around too much to stack on yet. Try it as a "
            "single habit first, or pick a steadier anchor."
        )

    return True, None


def add_habit(
    chain: Chain, habit_id: str, anchor_stability: Optional[StabilityReport]
) -> Chain:
    """Append a habit to the chain, enforcing §7."""
    allowed, reason = can_add(chain, anchor_stability)
    if not allowed:
        raise ChainError(reason or "cannot add to chain")
    if habit_id in chain.habit_ids:
        raise ChainError(f"habit {habit_id} is already in chain {chain.id}")
    return Chain(
        id=chain.id,
        anchor_id=chain.anchor_id,
        habit_ids=[*chain.habit_ids, habit_id],
    )


def prompt_target(chain: Chain, habits: Mapping[str, Habit]) -> Optional[str]:
    """The single habit in this chain that may carry a prompt.

    Returns None when the chain should be silent entirely — which happens in
    two cases, both intended:

    * the head has **graduated** (§7): the chain is by then a single
      behavioural unit, and that is the outcome we were aiming at, so
      prompting stops for the whole stack rather than falling through to link
      two;
    * the head is paused, retired, or faded to L4.

    Note it does *not* fall through to the next link when the head is merely
    lapsed. A lapsed head still gets its own recovery handling, and promoting
    link two to prompted would quietly convert the stack into two independent
    habits at the worst possible moment.
    """
    head_id = chain.head
    if head_id is None:
        return None

    head = habits.get(head_id)
    if head is None:
        return None

    if head.state in (HabitState.GRADUATED, HabitState.RETIRED, HabitState.PAUSED):
        return None

    if head.fade_level is FadeLevel.L4:
        return None

    return head_id


def should_prompt(habit_id: str, chain: Optional[Chain], habits: Mapping[str, Habit]) -> bool:
    """Whether this habit may be prompted, given its chain membership.

    A habit not in a chain is governed by its own fade level alone; the caller
    already handles that. This function exists to answer the chain question.
    """
    if chain is None or habit_id not in chain.habit_ids:
        return True
    return prompt_target(chain, habits) == habit_id


def chain_position(chain: Chain, habit_id: str) -> Optional[int]:
    """Zero-based position, or None if not a member."""
    try:
        return chain.habit_ids.index(habit_id)
    except ValueError:
        return None


def cue_for(chain: Chain, habit_id: str, habits: Mapping[str, Habit]) -> Optional[str]:
    """What cues this habit: the anchor for the head, the previous habit
    otherwise. This is the string the stack builder renders.
    """
    position = chain_position(chain, habit_id)
    if position is None:
        return None
    if position == 0:
        return f"After {chain.anchor_id}"
    previous = habits.get(chain.habit_ids[position - 1])
    if previous is None:
        return None
    return f"After {previous.title}"


def reorder(chain: Chain, habit_ids: Sequence[str]) -> Chain:
    """Reorder a chain, validating that membership is unchanged."""
    if sorted(habit_ids) != sorted(chain.habit_ids):
        raise ChainError("reorder must preserve chain membership")
    return Chain(id=chain.id, anchor_id=chain.anchor_id, habit_ids=list(habit_ids))


def remove_habit(chain: Chain, habit_id: str) -> Chain:
    """Remove a habit. Removing the head promotes the next link.

    This is a user action, unlike the graduation case in :func:`prompt_target`
    — someone who deliberately removes the first step of their stack is asking
    for the second to become the start of it.
    """
    if habit_id not in chain.habit_ids:
        raise ChainError(f"habit {habit_id} is not in chain {chain.id}")
    return Chain(
        id=chain.id,
        anchor_id=chain.anchor_id,
        habit_ids=[h for h in chain.habit_ids if h != habit_id],
    )
