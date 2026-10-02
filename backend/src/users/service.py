"""Users service — get-or-create from Kratos identity."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.kratos import KratosIdentity
from src.users.models import User


async def get_or_create_user(
    db: AsyncSession, identity: KratosIdentity
) -> User:
    """
    Called on every authenticated request.
    Returns the User row, creating it on first login.
    """
    result = await db.execute(
        select(User).where(User.kratos_identity_id == identity.kratos_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            kratos_identity_id=identity.kratos_id,
            email=identity.email,
        )
        db.add(user)
        await db.flush()

    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
