"""
Integration tests for Calendar Integration & Conflict Detection APIs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.core.database import Base, get_db
from src.core.kratos import KratosIdentity, get_current_identity
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from src.habits.conflict_models import ConflictAlert
from src.occurrences.models import Occurrence
from src.users.models import User
from src.habits.models import Anchor, Habit
from sqlalchemy import select

# StaticPool: in-memory SQLite hands out a new empty database per connection,
# so without pinning to one connection the schema created below is invisible to
# the request handler.
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session
        await session.commit()

MOCK_KRATOS_ID = str(uuid.uuid4())
# example.com is reserved for examples (RFC 2606) and validates. `.local` is a
# special-use name that email-validator rejects, which fails EmailStr at
# response-serialisation time rather than anywhere obvious.
mock_identity = KratosIdentity(
    kratos_id=MOCK_KRATOS_ID, email="conflict@ritual.example.com", session_token="mock"
)

async def override_get_current_identity():
    return mock_identity

UTC = timezone.utc

@pytest.fixture(autouse=True)
async def setup_db():
    """Schema and dependency overrides, per test — never at module import.

    Assigning `app.dependency_overrides` at import time made the two
    integration modules fight: import order decided which engine the app used,
    so this module's schema lived on one database while requests read another.
    """
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_identity] = override_get_current_identity
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_identity, None)


@pytest.mark.asyncio
async def test_conflict_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Fetch user to create them
        await client.get("/api/v1/users/me")

        now = datetime.now(UTC)

        # 2. Upload calendar blocks
        resp = await client.put(
            "/api/v1/users/me/calendar-blocks",
            json={
                "blocks": [
                    {
                        "start_time": (now + timedelta(hours=1)).isoformat(),
                        "end_time": (now + timedelta(hours=2)).isoformat()
                    }
                ]
            }
        )
        assert resp.status_code == 204

        # Let's seed the DB with an occurrence and a mock ConflictAlert to test the get/resolve endpoints
        async with TestingSessionLocal() as db:
            result = await db.execute(select(User).where(User.kratos_identity_id == MOCK_KRATOS_ID))
            user = result.scalar_one()

            anchor = Anchor(user_id=user.id, anchor_class="wake", label="w")
            db.add(anchor)
            await db.flush()

            habit = Habit(user_id=user.id, title="h", full_version="f", micro_version="m", anchor_id=anchor.id)
            db.add(habit)
            await db.flush()

            occ = Occurrence(
                habit_id=habit.id,
                scheduled_local=now + timedelta(hours=1, minutes=30),
                user_timezone="UTC",
                window_start=now + timedelta(hours=0),
                window_end=now + timedelta(hours=3),
                prompt_policy="prompt"
            )
            db.add(occ)
            await db.flush()

            alert = ConflictAlert(
                user_id=user.id,
                occurrence_id=occ.id,
                conflict_type="hard_calendar",
                description="Hard conflict",
                detected_for_date=now.date()
            )
            db.add(alert)
            await db.commit()
            
            # Keep the UUID, not str(...): it is only ever used as a query
            # value below, and the id columns bind uuid.UUID. A str reaches the
            # type's bind processor and dies on `value.hex` deep in the driver.
            occ_id = occ.id
            alert_id = str(alert.id)

        # 3. GET Conflicts
        resp = await client.get("/api/v1/habits/conflicts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) == 1
        assert alerts[0]["conflict_type"] == "hard_calendar"
        assert alerts[0]["status"] == "pending"

        # 4. Resolve Conflict with "rest"
        resp = await client.post(
            f"/api/v1/habits/conflicts/{alert_id}/resolve",
            json={"action": "rest"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved_rest"

        # Verify occurrence outcome was updated to 'rest'
        async with TestingSessionLocal() as db:
            result = await db.execute(select(Occurrence).where(Occurrence.id == occ_id))
            occ = result.scalar_one()
            assert occ.outcome == "rest"

        # 5. Try resolving again (should fail)
        resp = await client.post(
            f"/api/v1/habits/conflicts/{alert_id}/resolve",
            json={"action": "ignore"}
        )
        assert resp.status_code == 400
