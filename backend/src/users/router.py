"""Users router."""
from __future__ import annotations

from fastapi import APIRouter

from src.core.deps import DB, CurrentIdentity
from src.users import service
from src.users.models import CalendarBlock
from src.users.schemas import UserRead, UserUpdate, CalendarBlocksUpload

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(db: DB, identity: CurrentIdentity) -> UserRead:
    user = await service.get_or_create_user(db, identity)
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    body: UserUpdate,
    db: DB,
    identity: CurrentIdentity,
) -> UserRead:
    user = await service.get_or_create_user(db, identity)
    if body.elm_track is not None:
        user.elm_track = body.elm_track
    if body.timezone is not None:
        user.timezone = body.timezone
    await db.flush()
    return UserRead.model_validate(user)


@router.put("/me/calendar-blocks", status_code=204)
async def upload_calendar_blocks(
    body: CalendarBlocksUpload,
    db: DB,
    identity: CurrentIdentity,
) -> None:
    user = await service.get_or_create_user(db, identity)
    
    # 1. Delete all existing blocks for this user
    from sqlalchemy import delete
    await db.execute(delete(CalendarBlock).where(CalendarBlock.user_id == user.id))
    
    # 2. Insert the new 7-day horizon
    if body.blocks:
        db.add_all([
            CalendarBlock(
                user_id=user.id,
                start_time=b.start_time,
                end_time=b.end_time,
            )
            for b in body.blocks
        ])
    
    await db.commit()

