from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any, Protocol

from backend.application.ports import DraftSpec


class RetryableConnectorError(Exception):
    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class ConnectorPage[T]:
    records: tuple[T, ...]
    next_cursor: str | None
    checkpoint: str


@dataclass(frozen=True, slots=True)
class MisaRecord:
    kind: str
    external_id: str
    version: str
    occurred_at: datetime
    data: dict[str, Any]


class MisaPort(Protocol):
    async def fetch(self, *, cursor: str | None) -> ConnectorPage[MisaRecord]: ...


@dataclass(frozen=True, slots=True)
class MisaSyncResult:
    records: tuple[MisaRecord, ...]
    checkpoint: str
    duplicates: int
    attempts: int


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    entity: str
    external_id: str
    external_version: str
    source_timestamp: datetime
    values: dict[str, Any]
    provenance: dict[str, str]


def normalize_misa_record(record: MisaRecord) -> CanonicalRecord:
    required_by_kind = {
        "customer": {"code", "name"},
        "invoice": {
            "customer_code",
            "invoice_number",
            "issue_date",
            "due_date",
            "amount_minor",
            "outstanding_minor",
            "currency",
        },
        "payment": {"external_id", "booked_date", "amount_minor", "currency", "reference"},
    }
    if record.kind not in required_by_kind:
        raise ValueError("unsupported MISA record kind")
    missing = required_by_kind[record.kind] - set(record.data)
    if missing:
        raise ValueError(f"MISA {record.kind} record missing: {', '.join(sorted(missing))}")
    return CanonicalRecord(
        record.kind,
        record.external_id,
        record.version,
        record.occurred_at,
        record.data,
        {"provider": "misa", "external_id": record.external_id, "version": record.version},
    )


async def sync_misa(
    source: MisaPort,
    *,
    cursor: str | None,
    known_versions: set[tuple[str, str]],
    max_attempts: int = 3,
) -> MisaSyncResult:
    records: list[MisaRecord] = []
    duplicates = 0
    attempts = 0
    checkpoint = cursor or ""
    next_cursor = cursor
    while True:
        for attempt in range(1, max_attempts + 1):
            attempts += 1
            try:
                page = await source.fetch(cursor=next_cursor)
                break
            except RetryableConnectorError as exc:
                if attempt == max_attempts:
                    raise
                await asyncio.sleep(exc.retry_after_seconds or min(2 ** (attempt - 1), 8))
        for record in page.records:
            identity = (record.external_id, record.version)
            if identity in known_versions:
                duplicates += 1
                continue
            known_versions.add(identity)
            records.append(record)
        checkpoint = page.checkpoint
        next_cursor = page.next_cursor
        if next_cursor is None:
            break
    return MisaSyncResult(tuple(records), checkpoint, duplicates, attempts)


@dataclass(frozen=True, slots=True)
class OutlookMessage:
    external_id: str
    conversation_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    received_at: datetime
    attachment_ids: tuple[str, ...] = ()


class OutlookPort(Protocol):
    async def delta(self, *, delta_link: str | None) -> ConnectorPage[OutlookMessage]: ...

    async def create_draft(self, *, idempotency_key: str, spec: DraftSpec) -> str: ...


@dataclass(frozen=True, slots=True)
class OutlookSyncResult:
    messages: tuple[OutlookMessage, ...]
    delta_link: str


def normalize_outlook_message(message: OutlookMessage) -> dict[str, Any]:
    return {
        "provider": "outlook",
        "external_id": message.external_id,
        "thread_id": message.conversation_id,
        "direction": "INBOUND",
        "sender": message.sender,
        "recipients": list(message.recipients),
        "subject": message.subject,
        "body": message.body,
        "received_at": message.received_at,
        "attachment_external_ids": list(message.attachment_ids),
    }


async def sync_outlook(source: OutlookPort, *, delta_link: str | None) -> OutlookSyncResult:
    messages: dict[str, OutlookMessage] = {}
    next_link = delta_link
    checkpoint = delta_link or ""
    while True:
        page = await source.delta(delta_link=next_link)
        for message in page.records:
            messages[message.external_id] = message
        checkpoint = page.checkpoint
        next_link = page.next_cursor
        if next_link is None:
            break
    return OutlookSyncResult(tuple(messages.values()), checkpoint)


def graph_webhook_is_new(
    *, client_state: str, expected_state: str, event_id: str, seen: set[str]
) -> bool:
    if not expected_state or client_state != expected_state:
        raise PermissionError("invalid Microsoft Graph clientState")
    if event_id in seen:
        return False
    seen.add(event_id)
    return True


def graph_subscription_needs_renewal(expires_at: datetime, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    return expires_at <= current.replace(microsecond=0) + timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class ZaloTemplate:
    template_id: str
    version: int
    locale: str
    allowed_variables: frozenset[str]
    contains_sensitive_detail: bool = False


@dataclass(frozen=True, slots=True)
class ZaloRecipient:
    recipient_id: str
    verified: bool
    consented: bool
    is_group: bool = False
    suppressed: bool = False


@dataclass(frozen=True, slots=True)
class ZaloPreview:
    recipient_id: str
    template_id: str
    template_version: int
    variables: dict[str, str]
    dry_run: bool
    policy_checks: tuple[str, ...]


class ZaloPort(Protocol):
    async def deliver(self, *, idempotency_key: str, preview: ZaloPreview) -> str: ...


@dataclass(frozen=True, slots=True)
class ZaloDispatchResult:
    status: str
    external_id: str | None
    idempotency_key: str


async def dispatch_zalo_notification(
    *,
    preview: ZaloPreview,
    approval_status: str,
    idempotency_key: str,
    adapter: ZaloPort,
) -> ZaloDispatchResult:
    if approval_status != "APPROVED":
        raise PermissionError("valid human approval is required")
    if preview.dry_run:
        return ZaloDispatchResult("DRY_RUN", None, idempotency_key)
    external_id = await adapter.deliver(idempotency_key=idempotency_key, preview=preview)
    return ZaloDispatchResult("DELIVERED", external_id, idempotency_key)


def preview_zalo_notification(
    *,
    template: ZaloTemplate,
    recipient: ZaloRecipient,
    variables: dict[str, str],
    now_local: time,
    quiet_hours: tuple[time, time] = (time(20), time(8)),
    dry_run: bool = True,
) -> ZaloPreview:
    if not recipient.verified or not recipient.consented or recipient.suppressed:
        raise PermissionError("recipient is not verified, consented and eligible")
    if recipient.is_group and template.contains_sensitive_detail:
        raise PermissionError("sensitive debt detail is prohibited for group recipients")
    if set(variables) != set(template.allowed_variables):
        raise ValueError("template variables do not match the published registry")
    start, end = quiet_hours
    in_quiet_hours = now_local >= start or now_local < end
    if in_quiet_hours:
        raise PermissionError("notification blocked by quiet hours")
    return ZaloPreview(
        recipient.recipient_id,
        template.template_id,
        template.version,
        variables,
        dry_run,
        ("verified", "consented", "template_valid", "quiet_hours_clear"),
    )
