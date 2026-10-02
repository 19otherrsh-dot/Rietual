"""Model registry.

SQLAlchemy only knows about a table once its module has been imported, so every
model module must be imported before `Base.metadata` is used — for
`create_all`, for Alembic autogeneration, or for resolving a ForeignKey.

Previously this knowledge lived only in `alembic/env.py`. The application and
the tests relied on model modules being pulled in transitively by their
routers, which worked for every package except `occurrences` — it has no router,
so `occurrences` was absent from the metadata and

    misses.scheduled_occurrence_id -> occurrences.id

failed to resolve with NoReferencedTableError as soon as anything called
`create_all`. The failure surfaced in the integration test, but it would have
hit any code path that built the schema outside Alembic.

Import this module rather than remembering the list. `src.main` does at
startup, and `alembic/env.py` does for autogeneration.
"""

from __future__ import annotations

from src.core.database import Base

import src.users.models  # noqa: F401  isort:skip
import src.habits.models  # noqa: F401  isort:skip
import src.habits.conflict_models  # noqa: F401  isort:skip
import src.plans.models  # noqa: F401  isort:skip
import src.occurrences.models  # noqa: F401  isort:skip
import src.failure_layer.models  # noqa: F401  isort:skip
import src.instruments.models  # noqa: F401  isort:skip
import src.notifications.models  # noqa: F401  isort:skip

__all__ = ["Base"]
