"""Notifications router — device token registration."""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from src.core.deps import DB, CurrentIdentity
from src.notifications.models import DeviceToken
from src.users.service import get_or_create_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class TokenRegister(BaseModel):
    platform: str   # ios | android | fdroid
    token: str


@router.post("/register-token", status_code=status.HTTP_204_NO_CONTENT)
async def register_token(
    body: TokenRegister, db: DB, identity: CurrentIdentity
) -> None:
    user = await get_or_create_user(db, identity)
    # Upsert: update last_seen_at if token exists
    from sqlalchemy import select
    from datetime import datetime, timezone
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token == body.token)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.last_seen_at = datetime.now(timezone.utc)
    else:
        db.add(DeviceToken(
            user_id=user.id,
            platform=body.platform,
            token=body.token,
        ))
