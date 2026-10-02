"""Users schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    elm_track: str | None
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    elm_track: str | None = None
    timezone: str | None = None


class CalendarBlockCreate(BaseModel):
    start_time: datetime
    end_time: datetime

class CalendarBlocksUpload(BaseModel):
    blocks: list[CalendarBlockCreate]

