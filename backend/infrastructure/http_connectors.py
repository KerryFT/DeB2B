from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import httpx

from backend.application.ports import DraftSpec
from backend.application.v1_connectors import (
    ConnectorPage,
    MisaRecord,
    OutlookMessage,
    RetryableConnectorError,
)

TokenProvider = Callable[[], Awaitable[str]]


def _raise_connector_error(response: httpx.Response) -> None:
    if response.status_code in {408, 429, 500, 502, 503, 504}:
        retry_after = response.headers.get("retry-after")
        raise RetryableConnectorError(
            f"connector returned {response.status_code}",
            retry_after_seconds=float(retry_after)
            if retry_after and retry_after.isdigit()
            else None,
        )
    response.raise_for_status()


class MisaHttpAdapter:
    """Read-only adapter for a tenant's contracted MISA API surface.

    MISA product/API entitlements vary. The full vendor URL and record path therefore come from
    reviewed tenant configuration; this adapter intentionally exposes no write-back method.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        records_url: str,
        token_provider: TokenProvider,
    ) -> None:
        if not records_url.startswith("https://"):
            raise ValueError("MISA production URL must use HTTPS")
        self.client = client
        self.records_url = records_url
        self.token_provider = token_provider

    async def fetch(self, *, cursor: str | None) -> ConnectorPage[MisaRecord]:
        token = await self.token_provider()
        response = await self.client.get(
            self.records_url,
            params={"cursor": cursor} if cursor else {},
            headers={"authorization": f"Bearer {token}"},
            timeout=30,
        )
        _raise_connector_error(response)
        payload = response.json()
        records = tuple(
            MisaRecord(
                str(item["kind"]),
                str(item["id"]),
                str(item["version"]),
                datetime.fromisoformat(str(item["updated_at"])),
                dict(item["data"]),
            )
            for item in payload.get("records", [])
        )
        return ConnectorPage(records, payload.get("next_cursor"), str(payload["checkpoint"]))


class MicrosoftGraphMailAdapter:
    GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        mailbox: str,
        folder_id: str,
        token_provider: TokenProvider,
        allowed_recipients: frozenset[str],
    ) -> None:
        self.client = client
        self.mailbox = mailbox
        self.folder_id = folder_id
        self.token_provider = token_provider
        self.allowed_recipients = {item.casefold() for item in allowed_recipients}

    async def delta(self, *, delta_link: str | None) -> ConnectorPage[OutlookMessage]:
        token = await self.token_provider()
        url = delta_link or (
            f"{self.GRAPH_ROOT}/{'me' if self.mailbox == 'me' else f'users/{self.mailbox}'}/"
            f"mailFolders/{self.folder_id}/messages/delta"
        )
        if not url.startswith(self.GRAPH_ROOT):
            raise ValueError("untrusted Microsoft Graph delta link")
        response = await self.client.get(
            url,
            headers={
                "authorization": f"Bearer {token}",
                "prefer": 'outlook.body-content-type="text", odata.maxpagesize=100',
            },
            timeout=30,
        )
        _raise_connector_error(response)
        payload = response.json()
        messages = tuple(self._message(item) for item in payload.get("value", []))
        next_link = payload.get("@odata.nextLink")
        checkpoint = payload.get("@odata.deltaLink") or next_link
        if not checkpoint:
            raise ValueError("Graph delta response omitted continuation token")
        return ConnectorPage(messages, next_link, str(checkpoint))

    async def create_draft(self, *, idempotency_key: str, spec: DraftSpec) -> str:
        recipients = {item.casefold() for item in (*spec.to, *spec.cc)}
        if not recipients or not recipients <= self.allowed_recipients:
            raise PermissionError("draft recipient is not approved for this case")
        token = await self.token_provider()
        payload: dict[str, Any] = {
            "subject": spec.subject,
            "body": {"contentType": "Text", "content": spec.body},
            "toRecipients": [{"emailAddress": {"address": item}} for item in spec.to],
            "ccRecipients": [{"emailAddress": {"address": item}} for item in spec.cc],
            "internetMessageHeaders": [{"name": "x-ar-idempotency-key", "value": idempotency_key}],
        }
        mailbox_path = "me" if self.mailbox == "me" else f"users/{self.mailbox}"
        response = await self.client.post(
            f"{self.GRAPH_ROOT}/{mailbox_path}/messages",
            json=payload,
            headers={"authorization": f"Bearer {token}"},
            timeout=30,
        )
        _raise_connector_error(response)
        return str(response.json()["id"])

    @staticmethod
    def _message(item: dict[str, Any]) -> OutlookMessage:
        sender = item.get("from", {}).get("emailAddress", {}).get("address", "")
        recipients = tuple(
            entry.get("emailAddress", {}).get("address", "")
            for entry in item.get("toRecipients", [])
        )
        return OutlookMessage(
            str(item["id"]),
            str(item.get("conversationId", item["id"])),
            sender,
            recipients,
            str(item.get("subject", "")),
            str(item.get("body", {}).get("content", "")),
            datetime.fromisoformat(str(item["receivedDateTime"]).replace("Z", "+00:00")),
            tuple(),
        )
