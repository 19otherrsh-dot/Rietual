"""
Failure Layer — Pure state machine.

Reference: SPEC-failure-layer-v1 §2 (state machine), DECISIONS-v1 D1.

This module is intentionally stateless and has NO database dependency.
It takes a current state + event and returns the next state.
This makes it fully unit-testable in isolation (tests/unit/test_state_machine.py).

Key invariants enforced here:

  §3.1 — recovery content is NEVER delivered by push, at ANY depth.
         `push_side_trigger` is False on every transition in this module, and
         that is not an oversight. Recovery breaks are encountered in-app on
         next open. The only push permitted after a miss is a neutral,
         non-referential re-engagement at the next scheduled occurrence
         ("Tomorrow: [habit], [time]"), which is the prompt scheduler's job,
         not this module's.

  D1 — lapsed_1 produces nothing user-visible at all unless the user opens the
       app of their own accord. The transition is tracked (it drives
       skip-annotation capture, coping-plan seeding and the recovery metric)
       but has no surface: `recovery_break` is False. On a pull, the caller
       shows the inline light acknowledgment — see `ritual.engine.states`.

  D11 — Cue-stability feedback is NEVER surfaced in the recovery break context.
        Enforced by the recovery break API not including stability data in its
        response — not by this module, but documented here as the full policy.

  paused — checked first in every transition. A user in transition mode or
            with a pause clause active must never receive lapse logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HabitStateEnum(str, Enum):
    FORMING = "forming"
    ESTABLISHED = "established"
    GRADUATED = "graduated"
    LAPSED_1 = "lapsed_1"
    LAPSED_2 = "lapsed_2"
    DORMANT = "dormant"
    PAUSED = "paused"
    RETIRED = "retired"


class HabitEvent(str, Enum):
    MISS = "miss"
    COMPLETION = "completion"
    PAUSE = "pause"
    RESUME = "resume"
    SRBAI_THRESHOLD_MET = "srbai_threshold_met"      # two consecutive biweekly measures
    GRADUATION_CRITERIA_MET = "graduation_criteria_met"  # SRBAI + L4 + 80% unprompted
    DORMANCY_THRESHOLD = "dormancy_threshold"        # 4 consecutive misses or 10d no interaction
    USER_RETIRED = "user_retired"
    DORMANT_TIMEOUT = "dormant_timeout"              # 21d in dormant → retire (with confirmation)


@dataclass(frozen=True)
class TransitionResult:
    new_state: HabitStateEnum
    # Whether to emit a push notification for this transition (D1: NEVER for lapsed_1)
    push_side_trigger: bool
    # Whether to emit a recovery break (in-app, pull or push per spec §3.1)
    recovery_break: bool
    # Notes for the event log
    note: str


# Transitions that are valid from any non-paused state
_UNIVERSAL_TRANSITIONS = {
    HabitEvent.PAUSE: TransitionResult(
        new_state=HabitStateEnum.PAUSED,
        push_side_trigger=False,
        recovery_break=False,
        note="Paused — all lapse logic suspended.",
    ),
    HabitEvent.USER_RETIRED: TransitionResult(
        new_state=HabitStateEnum.RETIRED,
        push_side_trigger=False,
        recovery_break=False,
        note="User-initiated retirement.",
    ),
}


def transition(
    current_state: HabitStateEnum,
    event: HabitEvent,
    consecutive_misses: int = 0,
) -> TransitionResult:
    """
    Pure state transition function.

    Args:
        current_state: The habit's current state.
        event: The event that occurred.
        consecutive_misses: Current streak of consecutive misses (used to
            distinguish lapsed_2 → dormant boundary).

    Returns:
        TransitionResult describing the new state and side-effect flags.

    Raises:
        ValueError: If the event is not valid for the current state.
    """
    # ── Paused state: only resume or retire ──────────────────────────────────
    if current_state == HabitStateEnum.PAUSED:
        if event == HabitEvent.RESUME:
            return TransitionResult(
                new_state=HabitStateEnum.FORMING,
                push_side_trigger=False,
                recovery_break=False,
                note="Resumed from pause → forming.",
            )
        if event == HabitEvent.USER_RETIRED:
            return _UNIVERSAL_TRANSITIONS[HabitEvent.USER_RETIRED]
        raise ValueError(
            f"Event {event!r} is not valid while habit is paused. "
            "Only RESUME and USER_RETIRED are accepted."
        )

    # ── Universal transitions from any non-paused state ───────────────────────
    if event in _UNIVERSAL_TRANSITIONS:
        return _UNIVERSAL_TRANSITIONS[event]

    # ── forming → * ──────────────────────────────────────────────────────────
    if current_state == HabitStateEnum.FORMING:
        if event == HabitEvent.MISS:
            # D1: lapsed_1 has NO push-side trigger.
            # "After one miss most people have not registered a failure.
            #  Surfacing it tells them one occurred."
            return TransitionResult(
                new_state=HabitStateEnum.LAPSED_1,
                push_side_trigger=False,   # ← D1 enforced here
                recovery_break=False,      # pull-only; see §2.3
                note="First miss → lapsed_1. No push. Pull acknowledgment only if user opens app.",
            )
        if event == HabitEvent.SRBAI_THRESHOLD_MET:
            return TransitionResult(
                new_state=HabitStateEnum.ESTABLISHED,
                push_side_trigger=False,
                recovery_break=False,
                note="SRBAI threshold met → established.",
            )

    # ── lapsed_1 → * ─────────────────────────────────────────────────────────
    if current_state == HabitStateEnum.LAPSED_1:
        if event == HabitEvent.COMPLETION:
            return TransitionResult(
                new_state=HabitStateEnum.FORMING,
                push_side_trigger=False,
                recovery_break=False,
                note="Recovery from lapsed_1 → forming. Emits 'recovered' event.",
            )
        if event == HabitEvent.MISS:
            return TransitionResult(
                new_state=HabitStateEnum.LAPSED_2,
                # SPEC-failure-layer §3.1: recovery content is NEVER delivered by
                # push, at any depth. It is encountered in-app on next open. A
                # push saying "you missed your habit" is the shame vector this
                # whole section exists to prevent. D1 removed the lapsed_1
                # surface entirely; the no-push rule is older and broader, and
                # applies here too.
                push_side_trigger=False,
                recovery_break=True,
                note=(
                    "Second consecutive miss → lapsed_2. Recovery break available "
                    "in-app on next open. No push (§3.1)."
                ),
            )

    # ── lapsed_2 → * ─────────────────────────────────────────────────────────
    if current_state == HabitStateEnum.LAPSED_2:
        if event == HabitEvent.COMPLETION:
            return TransitionResult(
                new_state=HabitStateEnum.FORMING,
                push_side_trigger=False,
                recovery_break=False,
                note="Recovery from lapsed_2 → forming. Emits 'recovered_deep' event.",
            )
        if event == HabitEvent.MISS:
            # 4th consecutive miss or 10d no interaction → dormant
            if consecutive_misses >= 4:
                return TransitionResult(
                    new_state=HabitStateEnum.DORMANT,
                    push_side_trigger=False,  # no push into dormant
                    recovery_break=False,
                    note=f"Dormancy threshold ({consecutive_misses} consecutive misses) → dormant.",
                )
            return TransitionResult(
                new_state=HabitStateEnum.LAPSED_2,
                push_side_trigger=False,
                recovery_break=False,
                note="Additional miss while already lapsed_2.",
            )
        if event == HabitEvent.DORMANCY_THRESHOLD:
            return TransitionResult(
                new_state=HabitStateEnum.DORMANT,
                push_side_trigger=False,
                recovery_break=False,
                note="10d no interaction → dormant.",
            )

    # ── dormant → * ──────────────────────────────────────────────────────────
    if current_state == HabitStateEnum.DORMANT:
        if event in (HabitEvent.COMPLETION, HabitEvent.MISS):
            # Any completion or user-initiated re-plan → forming
            return TransitionResult(
                new_state=HabitStateEnum.FORMING,
                push_side_trigger=False,
                recovery_break=True,       # dormant_return recovery break
                note="Return from dormant → forming. dormant_return recovery break.",
            )
        if event == HabitEvent.DORMANT_TIMEOUT:
            # 21d in dormant — must be confirmed by user before retiring
            return TransitionResult(
                new_state=HabitStateEnum.RETIRED,
                push_side_trigger=False,
                recovery_break=False,
                note="21d dormant timeout → retired (requires user confirmation before applying).",
            )

    # ── established → * ──────────────────────────────────────────────────────
    if current_state == HabitStateEnum.ESTABLISHED:
        if event == HabitEvent.GRADUATION_CRITERIA_MET:
            return TransitionResult(
                new_state=HabitStateEnum.GRADUATED,
                push_side_trigger=False,
                recovery_break=False,
                note="Graduation criteria met → graduated.",
            )
        if event == HabitEvent.MISS:
            # Established habits still lapse — revert to forming first
            return TransitionResult(
                new_state=HabitStateEnum.LAPSED_1,
                push_side_trigger=False,   # D1 applies here too
                recovery_break=False,
                note="Established habit missed → lapsed_1.",
            )

    # ── graduated → * ────────────────────────────────────────────────────────
    if current_state == HabitStateEnum.GRADUATED:
        if event == HabitEvent.MISS:
            # Maintenance check showed decay — re-entry is offered, not forced
            return TransitionResult(
                new_state=HabitStateEnum.FORMING,
                push_side_trigger=False,
                recovery_break=False,
                note="Graduated habit decay detected → re-entry offered to forming.",
            )

    raise ValueError(
        f"No valid transition from state={current_state!r} on event={event!r}. "
        "Check the state machine spec (SPEC-failure-layer §2.1)."
    )
