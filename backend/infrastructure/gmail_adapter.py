from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any

from backend.application.ports import DraftSpec


class GmailDraftAdapter:
    """Create-only Gmail adapter. Intentionally exposes no send operation."""

    def __init__(
        self, service: Any, *, allowed_recipients: frozenset[str], user_id: str = "me"
    ) -> None:
        self.service = service
        self.allowed_recipients = {address.casefold() for address in allowed_recipients}
        self.user_id = user_id

    async def create_draft(self, *, idempotency_key: str, spec: DraftSpec) -> str:
        recipients = {address.casefold() for address in (*spec.to, *spec.cc)}
        if not recipients or not recipients <= self.allowed_recipients:
            raise PermissionError("draft recipient is not approved for this case")
        message = EmailMessage()
        message["To"] = ", ".join(spec.to)
        if spec.cc:
            message["Cc"] = ", ".join(spec.cc)
        message["Subject"] = spec.subject
        message["X-AR-Idempotency-Key"] = idempotency_key
        message.set_content(spec.body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        response = (
            self.service.users()
            .drafts()
            .create(userId=self.user_id, body={"message": {"raw": raw}})
            .execute()
        )
        return str(response["id"])
