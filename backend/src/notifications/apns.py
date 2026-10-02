"""
APNs push dispatcher — direct HTTP/2, no Firebase, no OneSignal.

Reference: STACK §2 ("talking to APNs directly from our own server
with an open source client library — no Firebase, no OneSignal, no vendor in the path").

Uses JWT-based authentication (provider auth token, not certificates).
Token is cached and refreshed every 55 minutes (Apple rotates every 60).
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import jwt

from src.core.config import Settings


_token_cache: dict[str, object] = {"token": None, "issued_at": 0.0}
_TOKEN_TTL_SECONDS = 55 * 60  # refresh every 55 min (Apple invalidates at 60)


def _get_apns_token(settings: Settings) -> str:
    """Generate (or return cached) APNs JWT provider token."""
    now = time.time()
    if _token_cache["token"] and (now - _token_cache["issued_at"]) < _TOKEN_TTL_SECONDS:
        return str(_token_cache["token"])

    key_path: Path = settings.apns_private_key_path
    private_key = key_path.read_text()

    token = jwt.encode(
        payload={
            "iss": settings.apns_team_id,
            "iat": int(now),
        },
        key=private_key,
        algorithm="ES256",
        headers={"kid": settings.apns_key_id},
    )
    _token_cache["token"] = token
    _token_cache["issued_at"] = now
    return token


async def send_apns(
    device_token: str,
    payload: dict,
    settings: Settings,
    apns_id: str | None = None,
) -> bool:
    """
    Send a push notification to one iOS device via APNs HTTP/2.

    Returns True on success (202 Accepted), False otherwise.
    """
    token = _get_apns_token(settings)
    notification_id = apns_id or str(uuid.uuid4())

    url = f"https://{settings.apns_host}/3/device/{device_token}"

    headers = {
        "authorization": f"bearer {token}",
        "apns-topic": settings.apns_bundle_id,
        "apns-id": notification_id,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }

    async with httpx.AsyncClient(http2=True) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
            return resp.status_code == 200
        except httpx.RequestError:
            return False
