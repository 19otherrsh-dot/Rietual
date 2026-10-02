"""Plans schemas — WOOP and if-then."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class PlanCreate(BaseModel):
    plan_type: str          # "woop" | "if_then"
    created_via: str        # "onboarding_proper" | "onboarding_quick" | "first_lapse" | "replanning"

    # WOOP fields — required when plan_type == "woop"
    wish_text: str | None = None
    outcome_text: str | None = None
    obstacle_text: str | None = None       # unbounded, stored verbatim (D6)
    obstacle_class: str | None = None      # "internal" | "external_accepted"
    obstacle_source: str | None = None     # "freetext" | "picker" | "after_drilldown"
    outcome_imagined_seconds: float | None = None
    obstacle_imagined_seconds: float | None = None
    drilldown_used: bool = False

    # Common
    plan_response_text: str | None = None  # the if-then response

    @field_validator("plan_type")
    @classmethod
    def valid_plan_type(cls, v: str) -> str:
        if v not in {"woop", "if_then"}:
            raise ValueError("plan_type must be 'woop' or 'if_then'")
        return v

    @field_validator("obstacle_text")
    @classmethod
    def obstacle_text_not_truncated(cls, v: str | None) -> str | None:
        # No max length — this is enforced at the model level too (TEXT column).
        # Validator exists purely to document the invariant.
        return v


class PlanRead(BaseModel):
    id: uuid.UUID
    habit_id: uuid.UUID
    plan_type: str
    created_via: str
    wish_text: str | None
    outcome_text: str | None
    obstacle_text: str | None
    obstacle_class: str | None
    plan_response_text: str | None
    created_at: datetime
    superseded_by: uuid.UUID | None

    model_config = {"from_attributes": True}
