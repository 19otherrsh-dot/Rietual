"""
FCM HTTP v1 API dispatcher — no Firebase SDK.

Reference: STACK §2 ("FCM is proprietary and is the only reliable transport
on stock Android. Accept FCM as transport only — payloads encrypted, no Firebase SDK,
no Firebase Analytics, HTTP v1 API called from our server").

Authenticates with a Google service account (OAuth2 token),
calls the FCM HTTP v1 REST endpoint directly.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

_FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

_token_cache: dict[str, object] = {"access_token": None, "expires_at": 0.0}


async def _get_fcm_token(service_account_path: Path) -> tuple[str, str]:
    """
    Obtain a short-lived OAuth2 access token from the Google token endpoint
    using service account credentials (JWT grant).

    Returns (access_token, project_id).
    """
    now = time.time()
    if _token_cache["access_token"] and now < float(str(_token_cache["expires_at"])):
        sa = json.loads(service_account_path.read_text())
        return str(_token_cache["access_token"]), sa["project_id"]

    sa = json.loads(service_account_path.read_text())

    import jwt  # imported here to keep the top-level import clean

    claim = {
        "iss": sa["client_email"],
        "scope": _FCM_SCOPE,
        "aud": _GOOGLE_TOKEN_URL,
        "iat": int(now),
        "exp": int(now) + 3600,
    }
    signed = jwt.encode(claim, sa["private_key"], algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600) - 60

    return data["access_token"], sa["project_id"]


async def send_fcm(
    device_token: str,
    payload: dict,
    service_account_path: Path,
) -> bool:
    """
    Send a push notification to one Android device via FCM HTTP v1.
    Returns True on success (200 OK).
    """
    access_token, project_id = await _get_fcm_token(service_account_path)
    url = _FCM_ENDPOINT.format(project_id=project_id)

    message = {
        "message": {
            "token": device_token,
            "notification": payload.get("notification", {}),
            "data": payload.get("data", {}),
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                url,
                json=message,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            return resp.status_code == 200
        except httpx.RequestError:
            return False
