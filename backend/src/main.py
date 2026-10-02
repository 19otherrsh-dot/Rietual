"""
RITUAL FastAPI application factory.
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.failure_layer.router import router as failure_layer_router
from src.habits.router import router as habits_router
from src.notifications.router import router as notifications_router
from src.plans.router import router as plans_router
from src.users.router import router as users_router

# Registers every ORM model on Base.metadata. Required because `occurrences`
# has no router and would otherwise never be imported, leaving the
# misses -> occurrences foreign key unresolvable. See src/models.py.
import src.models  # noqa: F401  isort:skip

logger = structlog.get_logger()

_settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="RITUAL API",
        description=(
            "Behavioral science-based habit & wellness platform. "
            "Phase 1 — Foundation & the Failure Layer."
        ),
        version="0.1.0",
        docs_url="/docs" if not _settings.is_production else None,
        redoc_url="/redoc" if not _settings.is_production else None,
    )

    # CORS (adjust origins for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if _settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(habits_router, prefix="/api/v1")
    app.include_router(plans_router, prefix="/api/v1")
    app.include_router(failure_layer_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "env": _settings.app_env}

    return app


app = create_app()
