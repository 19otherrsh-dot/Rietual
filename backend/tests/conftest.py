"""
conftest.py — shared pytest fixtures.

Every test that needs a database or an HTTP client takes it from here.

**Why this file exists in this shape.** Two integration modules previously each
built their own module-level engine and assigned
`app.dependency_overrides[get_db]` at import time. Import order then decided
which engine the app actually talked to, so one module created its schema on
engine A while the app read from engine B — surfacing as
`no such table: users`, which looks like a migration problem and is not one.
Module-level mutation of shared app state does not compose; fixtures do.

Two details that matter for in-memory SQLite:

* `StaticPool` plus a single connection. `sqlite+aiosqlite:///:memory:` gives a
  *new, empty database* per connection, so without this the schema created by
  the fixture is invisible to the request handler.
* Overrides are cleared after each test, so nothing leaks between modules.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.core.database import get_db
from src.core.kratos import KratosIdentity, get_current_identity
from src.main import app
from src.models import Base


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_engine() -> AsyncIterator:
    """A fresh in-memory database per test, shared across all connections."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_sessionmaker(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(db_sessionmaker) -> AsyncIterator[AsyncSession]:
    """A session for tests that drive services or workers directly."""
    async with db_sessionmaker() as session:
        yield session


@pytest.fixture
def identity() -> KratosIdentity:
    # example.com is reserved for documentation and examples (RFC 2606) and
    # validates. `.local` is a special-use name that email-validator rejects.
    return KratosIdentity(
        kratos_id=str(uuid.uuid4()),
        email="test@ritual.example.com",
        session_token="mock-token",
    )


@pytest.fixture
async def client(db_sessionmaker, identity) -> AsyncIterator[AsyncClient]:
    """An HTTP client wired to this test's database and a mock identity."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with db_sessionmaker() as session:
            yield session
            await session.commit()

    async def override_get_current_identity() -> KratosIdentity:
        return identity

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_identity] = override_get_current_identity
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            yield ac
    finally:
        # Never leak an override into another module.
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_identity, None)
