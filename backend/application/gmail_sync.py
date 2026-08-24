from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


class HistoryExpired(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MessagePage:
    message_ids: tuple[str, ...]
    next_page_token: str | None
    history_id: str


class GmailSyncSource(Protocol):
    async def list_page(self, *, label: str, page_token: str | None) -> MessagePage: ...

    async def history(self, *, cursor: str) -> MessagePage: ...


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    message_ids: tuple[str, ...]
    next_cursor: str
    full_sync: bool


async def initial_sync(source: GmailSyncSource, *, label: str) -> SyncOutcome:
    token = None
    ids: list[str] = []
    latest_cursor = ""
    while True:
        page = await source.list_page(label=label, page_token=token)
        ids.extend(page.message_ids)
        latest_cursor = page.history_id
        token = page.next_page_token
        if token is None:
            break
    return SyncOutcome(tuple(dict.fromkeys(ids)), latest_cursor, True)


async def incremental_sync(source: GmailSyncSource, *, cursor: str, label: str) -> SyncOutcome:
    try:
        page = await source.history(cursor=cursor)
        return SyncOutcome(tuple(dict.fromkeys(page.message_ids)), page.history_id, False)
    except HistoryExpired:
        return await initial_sync(source, label=label)


def should_renew_watch(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    return expires_at is None or expires_at <= current + timedelta(hours=24)


def notification_advances(current_cursor: str | None, received_history_id: str) -> bool:
    if current_cursor is None:
        return True
    try:
        return int(received_history_id) > int(current_cursor)
    except ValueError:
        return received_history_id != current_cursor
