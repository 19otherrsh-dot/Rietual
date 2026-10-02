"""
Ory Kratos session validation — FastAPI dependency.

Production path: reads X-Session-Token header, calls Kratos /sessions/whoami
via the Admin API, returns the verified identity.

Dev bypass (DEV_AUTH_BYPASS=true): reads X-Dev-User-Id header and returns a
synthetic identity object.  This path is locked out in production.

Reference: STACK §4 (Ory Kratos), DECISIONS-v1 plan note.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx
from fastapi import Depends, Header, HTTPException, status

from src.core.config import Settings, get_settings


@dataclass
class KratosIdentity:
    """Minimal identity object passed to route handlers."""

    kratos_id: str           # Kratos identity UUID
    email: str               # primary trait
    session_token: str       # raw token (may be empty in dev bypass)


async def get_current_identity(
    x_session_token: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> KratosIdentity:
    """
    FastAPI dependency.  Returns the verified Kratos identity for the request.
    Used by domain modules via CurrentIdentity = Annotated[KratosIdentity, Depends(...)].
    """
    # ── Production guard ──────────────────────────────────────────────────────
    if settings.dev_auth_bypass and settings.is_production:
        raise RuntimeError(
            "DEV_AUTH_BYPASS must never be enabled in production. "
            "Check your environment configuration."
        )

    # ── Dev bypass ────────────────────────────────────────────────────────────
    if settings.dev_auth_bypass:
        if not x_dev_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="DEV_AUTH_BYPASS is enabled: provide X-Dev-User-Id header.",
            )
        # Generate a deterministic-looking identity for the dev user ID
        return KratosIdentity(
            kratos_id=x_dev_user_id,
            email=f"dev+{x_dev_user_id[:8]}@ritual.local",
            session_token="",
        )

    # ── Production: Kratos session validation ─────────────────────────────────
    if not x_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Session-Token header.",
        )

    async with httpx.AsyncClient(base_url=settings.kratos_admin_url) as client:
        try:
            resp = await client.get(
                "/sessions",
                params={"expand": "Identity"},
                headers={"X-Session-Token": x_session_token},
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Auth service unreachable: {exc}",
            ) from exc

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid or expired.",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from auth service.",
        )

    data = resp.json()
    identity = data.get("identity", {})
    traits = identity.get("traits", {})

    return KratosIdentity(
        kratos_id=identity["id"],
        email=traits.get("email", ""),
        session_token=x_session_token,
    )
