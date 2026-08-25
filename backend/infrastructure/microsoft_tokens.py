from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select

from backend.infrastructure.config import Settings
from backend.infrastructure.database import tenant_session
from backend.infrastructure.gmail_oauth import CredentialCipher
from backend.infrastructure.models import ConnectorCredential


async def outlook_access_token(settings: Settings, *, tenant_id: str, account: str) -> str:
    from uuid import UUID

    tenant_uuid = UUID(tenant_id)
    cipher = CredentialCipher(settings.encryption_key_bytes)
    with tenant_session(tenant_uuid) as session:
        credential = session.scalar(
            select(ConnectorCredential).where(
                ConnectorCredential.tenant_id == tenant_uuid,
                ConnectorCredential.provider == "outlook",
                ConnectorCredential.account == account,
                ConnectorCredential.status == "CONNECTED",
            )
        )
        if credential is None:
            raise PermissionError("Outlook is not connected")
        payload = cipher.decrypt(credential.ciphertext, tenant_id=tenant_id)
        expires_at = credential.expires_at
    if expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=5):
        return str(payload["access_token"])
    refresh_token = str(payload.get("refresh_token", ""))
    if (
        not refresh_token
        or not settings.microsoft_client_id
        or not settings.microsoft_client_secret
    ):
        raise PermissionError("Outlook authorization must be renewed")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/token",
            data={
                "client_id": settings.microsoft_client_id,
                "client_secret": settings.microsoft_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "openid profile email offline_access User.Read Mail.ReadWrite",
            },
            timeout=30,
        )
    if response.status_code != 200:
        with tenant_session(tenant_uuid) as session:
            stale = session.scalar(
                select(ConnectorCredential).where(
                    ConnectorCredential.tenant_id == tenant_uuid,
                    ConnectorCredential.provider == "outlook",
                    ConnectorCredential.account == account,
                )
            )
            if stale is not None:
                stale.status = "REAUTH_REQUIRED"
        raise PermissionError("Outlook authorization must be renewed")
    refreshed: dict[str, Any] = response.json()
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh_token
    new_expiry = datetime.now(UTC) + timedelta(seconds=int(refreshed.get("expires_in", 3600)))
    with tenant_session(tenant_uuid) as session:
        credential = session.scalar(
            select(ConnectorCredential).where(
                ConnectorCredential.tenant_id == tenant_uuid,
                ConnectorCredential.provider == "outlook",
                ConnectorCredential.account == account,
            )
        )
        if credential is None:
            raise PermissionError("Outlook is not connected")
        credential.ciphertext = cipher.encrypt(refreshed, tenant_id=tenant_id)
        credential.expires_at = new_expiry
        credential.scopes = str(refreshed.get("scope", "")).split()
        credential.status = "CONNECTED"
    return str(refreshed["access_token"])
