"""
Shared FastAPI dependencies — type aliases used across all domain routers.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.kratos import KratosIdentity, get_current_identity

# Drop these into any route signature:
#   async def my_route(db: DB, identity: CurrentIdentity) -> ...:
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentIdentity = Annotated[KratosIdentity, Depends(get_current_identity)]
