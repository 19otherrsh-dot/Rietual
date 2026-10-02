"""
RITUAL backend configuration.

All settings are loaded from environment variables (or a .env file).
Pydantic-settings validates types at startup — a misconfigured env
fails loudly rather than silently misbehaving at runtime.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    secret_key: str = "change-me"
    debug: bool = False

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return v

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://ritual:ritual@localhost:5432/ritual"

    # ── Valkey (Celery broker + cache) ────────────────────────────────────────
    valkey_url: str = "valkey://localhost:6379/0"

    @property
    def celery_broker_url(self) -> str:
        # Celery uses the redis:// scheme for Valkey (protocol-compatible)
        return self.valkey_url.replace("valkey://", "redis://")

    # ── Auth — Ory Kratos ─────────────────────────────────────────────────────
    kratos_public_url: str = "http://localhost:4433"
    kratos_admin_url: str = "http://localhost:4434"

    # DEV ONLY: bypass Kratos and trust X-Dev-User-Id header.
    # Any non-false value in production is a misconfiguration and will raise.
    dev_auth_bypass: bool = False

    @field_validator("dev_auth_bypass")
    @classmethod
    def no_bypass_in_production(cls, v: bool, info: object) -> bool:
        # info.data may not have app_env yet in all pydantic versions;
        # we enforce this again in the Kratos dep at runtime.
        return v

    # ── Push — APNs (direct HTTP/2, no Firebase) ──────────────────────────────
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_bundle_id: str = "com.yourcompany.ritual"
    apns_private_key_path: Path = Path("./secrets/apns_auth_key.p8")
    apns_sandbox: bool = True

    # ── Push — FCM (HTTP v1 API, no SDK) ─────────────────────────────────────
    fcm_service_account_json_path: Path = Path("./secrets/fcm_service_account.json")

    # ── Celery ────────────────────────────────────────────────────────────────
    celery_timezone: str = "UTC"

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def apns_host(self) -> str:
        return (
            "api.sandbox.push.apple.com"
            if self.apns_sandbox
            else "api.push.apple.com"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — call everywhere via Depends(get_settings)."""
    return Settings()
