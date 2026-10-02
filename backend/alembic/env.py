"""
Alembic env.py — async SQLAlchemy support.

Imports all ORM models so Alembic can autogenerate migrations.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import get_settings

# Single registry — importing it registers every model on Base.metadata.
# Keep the list in src/models.py, not here, so the app, the tests and Alembic
# cannot disagree about which modules exist.
from src.models import Base  # noqa: F401
import src.users.models          # noqa: F401
import src.habits.models         # noqa: F401
import src.habits.conflict_models # noqa: F401
import src.plans.models          # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_settings = get_settings()


def run_migrations_offline() -> None:
    context.configure(
        url=_settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
