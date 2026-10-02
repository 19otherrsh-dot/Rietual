"""Core habit-engine types.

Implements SPEC-habit-engine-v1 §1 (object model).

Deliberately framework-free: no ORM, no FastAPI, no I/O. Every rule that the
launch gates in PLAN-phase1-v1 §7 care about lives in pure functions over these
types so it can be tested without infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Optional

# --------------------------------------------------------------------------
# States
# --------------------------------------------------------------------------


class HabitState(str, Enum):
    """SPEC-habit-engine §2.1."""

    FORMING = "forming"
    ESTABLISHED = "established"
    GRADUATED = "graduated"
    LAPSED_1 = "lapsed_1"
    LAPSED_2 = "lapsed_2"
    DORMANT = "dormant"
    PAUSED = "paused"
    RETIRED = "retired"


#: States in which lapse progression, fading advancement and probe days are all
#: suspended. SPEC-failure-layer §2.1 ("`paused` is load-bearing") and
#: SPEC-habit-engine §5.3.
LAPSE_SUSPENDED_STATES = frozenset(
    {HabitState.PAUSED, HabitState.GRADUATED, HabitState.RETIRED}
)

LAPSED_STATES = frozenset(
    {HabitState.LAPSED_1, HabitState.LAPSED_2, HabitState.DORMANT}
)


class Stability(str, Enum):
    """Cue-stability verdict for a single dimension. SPEC-habit-engine §3.1."""

    STABLE = "stable"
    VARIABLE = "variable"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


class StabilityBasis(str, Enum):
    """How a stability verdict was reached.

    Always shown to the user (SPEC-habit-engine §3.2): we never imply a score is
    observed when it is a prior.
    """

    PRIOR = "prior"
    CALENDAR = "calendar"
    OBSERVED = "observed"


class AnchorClass(str, Enum):
    """SPEC-habit-engine §3.4."""

    WAKE = "wake"
    FIRST_COFFEE = "first_coffee"
    COMMUTE_START = "commute_start"
    LUNCH = "lunch"
    WORK_END = "work_end"
    DINNER = "dinner"
    BEDTIME = "bedtime"
    CUSTOM = "custom"


class FadeLevel(IntEnum):
    """Reminder-fading ladder. SPEC-habit-engine §5.1."""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4

    @property
    def prompts_per_week(self) -> int:
        return {0: 7, 1: 5, 2: 3, 3: 1, 4: 0}[int(self)]


class PromptPolicy(str, Enum):
    """Per-occurrence prompt decision, assigned when occurrences are
    materialised so probe days can be planned rather than decided at fire time
    (SPEC-habit-engine §4.1)."""

    PROMPT = "prompt"
    SUPPRESS = "suppress"
    PROBE = "probe"


class Outcome(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    MISSED = "missed"
    REST = "rest"
    #: A miss on a day where we deliberately withheld the prompt. Excluded from
    #: lapse progression and streak loss: we caused it, so we absorb it.
    #: SPEC-habit-engine §5.3.
    PROBE_MISS = "probe_miss"


class CompletionSource(str, Enum):
    APP = "app"
    WIDGET = "widget"
    WATCH = "watch"
    INTEGRATION = "integration"


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StabilityReport:
    """The weakest dimension, never a composite. SPEC-habit-engine §3.1.

    We do not average the three dimensions because we cannot validate the
    weights and a composite hides the actionable part.
    """

    verdict: Stability
    basis: StabilityBasis
    weakest_dimension: Optional[str]
    detail: dict[str, Stability] = field(default_factory=dict)
    sample_size: int = 0
    provisional: bool = False


@dataclass
class Anchor:
    id: str
    user_id: str
    anchor_class: AnchorClass
    label: str
    #: Local wall-clock time of day, e.g. "07:00". None for pure event anchors.
    nominal_time: Optional[str] = None
    stability: Optional[StabilityReport] = None


@dataclass
class Habit:
    id: str
    user_id: str
    title: str
    full_version: str
    micro_version: str
    anchor_id: str
    #: IANA identifier, e.g. "Europe/London". Occurrences are generated in local
    #: wall clock, never UTC. SPEC-habit-engine §4.2.
    timezone: str
    state: HabitState = HabitState.FORMING
    fade_level: FadeLevel = FadeLevel.L0
    journey_id: Optional[str] = None
    plan_type: str = "if_then"  # woop | if_then  (SPEC-onboarding §8, D5)
    created_at: Optional[datetime] = None
    #: Set when a `forgot`-class coping plan restores prompting. Time-boxed to
    #: 7 days so fading does not unravel through the coping-plan door.
    #: SPEC-habit-engine §5.1.
    prompt_restore_until: Optional[datetime] = None
    fade_level_before_restore: Optional[FadeLevel] = None


@dataclass
class Occurrence:
    id: str
    habit_id: str
    #: Timezone-aware, in the habit's local zone.
    scheduled_local: datetime
    window_start: datetime
    window_end: datetime
    prompt_policy: PromptPolicy = PromptPolicy.PROMPT
    prompt_sent_at: Optional[datetime] = None
    #: Delivery, not send, governs attribution. A prompt sent at 07:00 and
    #: delivered at 09:40 when the phone came off airplane mode did not cause an
    #: 08:15 completion. SPEC-habit-engine §6.1.
    prompt_delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_source: Optional[CompletionSource] = None
    outcome: Outcome = Outcome.PENDING

    @property
    def was_prompted(self) -> bool:
        return self.prompt_delivered_at is not None
