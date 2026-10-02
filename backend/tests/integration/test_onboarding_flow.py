"""
Integration tests for the Onboarding Flow.

Simulates the screen 1 → screen 13 API flow from SPEC-onboarding-v1.
We mock the database and Kratos auth for this integration test.
"""
from __future__ import annotations

import uuid
from datetime import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import Base, get_db
from src.core.kratos import KratosIdentity, get_current_identity
from src.main import app

# In-memory SQLite gives a NEW, EMPTY database per connection, so the schema
# this module creates would otherwise be invisible to the request handler.
# StaticPool pins the whole module to one connection.
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session
        await session.commit()

# Mock user for testing
MOCK_KRATOS_ID = str(uuid.uuid4())
mock_identity = KratosIdentity(
    kratos_id=MOCK_KRATOS_ID,
    email="test@ritual.example.com",
    session_token="mock-token"
)

async def override_get_current_identity():
    return mock_identity

@pytest.fixture(autouse=True)
async def setup_db():
    """Schema and dependency overrides, per test.

    The overrides used to be assigned at module import. With two integration
    modules doing that, import order decided which engine the app actually
    talked to — one module created its schema on engine A while the app read
    from engine B, which surfaced as `no such table: users` and looks like a
    migration problem. Applying and removing them per test is what makes the
    modules independent of import order.
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
async def test_onboarding_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        
        # 1. Fetch user (creates User record implicitly via get_or_create)
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 200
        user_data = resp.json()
        assert user_data["email"] == "test@ritual.example.com"

        # 2. Update user with ELM track and timezone (Screen 5/6)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"elm_track": "central", "timezone": "America/New_York"}
        )
        assert resp.status_code == 200
        assert resp.json()["elm_track"] == "central"

        # 3. Create Anchor (Screen 7/8)
        resp = await client.post(
            "/api/v1/habits/anchors",
            json={
                "anchor_class": "wake",
                "label": "After I wake up",
                "nominal_time": "07:00:00"
            }
        )
        assert resp.status_code == 201
        anchor_data = resp.json()
        anchor_id = anchor_data["id"]
        assert anchor_data["anchor_class"] == "wake"

        # 4. Create Habit (Screen 9/10)
        resp = await client.post(
            "/api/v1/habits",
            json={
                "title": "Drink water",
                "full_version": "Drink 16oz of water from the kitchen",
                "micro_version": "Take one sip of water",
                "anchor_id": anchor_id
            }
        )
        assert resp.status_code == 201
        habit_data = resp.json()
        habit_id = habit_data["id"]
        assert habit_data["micro_version"] == "Take one sip of water"

        # 5. Create WOOP Plan (Screen 11/12)
        resp = await client.post(
            f"/api/v1/habits/{habit_id}/plans",
            json={
                "plan_type": "woop",
                "created_via": "onboarding_proper",
                "wish_text": "Feel hydrated",
                "outcome_text": "More energy in the morning",
                "obstacle_text": "I forget to fill the glass",
                "obstacle_class": "internal",
                "obstacle_source": "freetext",
                "outcome_imagined_seconds": 15.0,
                "obstacle_imagined_seconds": 12.0,
                "drilldown_used": False,
                "plan_response_text": "I will fill a glass and leave it on the nightstand"
            }
        )
        assert resp.status_code == 201
        plan_data = resp.json()
        assert plan_data["plan_type"] == "woop"
        assert plan_data["obstacle_text"] == "I forget to fill the glass"

        # 6. Fetch active plan
        resp = await client.get(f"/api/v1/habits/{habit_id}/plans/active")
        assert resp.status_code == 200
        active_plan = resp.json()
        assert active_plan["id"] == plan_data["id"]
