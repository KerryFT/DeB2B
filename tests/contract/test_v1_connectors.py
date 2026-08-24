from datetime import UTC, datetime

import pytest

from backend.application.ports import DraftSpec
from backend.application.v1_connectors import (
    ConnectorPage,
    MisaRecord,
    OutlookMessage,
    ZaloRecipient,
    ZaloTemplate,
    dispatch_zalo_notification,
    normalize_misa_record,
    normalize_outlook_message,
    preview_zalo_notification,
    sync_misa,
    sync_outlook,
)
from backend.infrastructure.v1_fakes import FakeMisa, FakeOutlook, FakeZalo


@pytest.mark.asyncio
async def test_misa_incremental_pagination_throttling_and_duplicate_replay() -> None:
    first = MisaRecord(
        "customer",
        "CUS-1",
        "v1",
        datetime(2026, 8, 1, tzinfo=UTC),
        {"code": "CUS-1", "name": "Synthetic customer"},
    )
    duplicate = MisaRecord(
        "customer",
        "CUS-1",
        "v1",
        datetime(2026, 8, 1, tzinfo=UTC),
        {"code": "CUS-1", "name": "Synthetic customer"},
    )
    invoice = MisaRecord(
        "invoice", "INV-1", "v2", datetime(2026, 8, 2, tzinfo=UTC), {"invoice_number": "INV-1"}
    )
    fake = FakeMisa(
        {
            None: ConnectorPage((first,), "page-2", "checkpoint-1"),
            "page-2": ConnectorPage((duplicate, invoice), None, "checkpoint-2"),
        },
        throttle_once=True,
    )
    known: set[tuple[str, str]] = set()
    result = await sync_misa(fake, cursor=None, known_versions=known)
    assert [item.external_id for item in result.records] == ["CUS-1", "INV-1"]
    assert result.duplicates == 1
    assert result.checkpoint == "checkpoint-2"
    assert result.attempts == 3
    assert normalize_misa_record(result.records[0]).provenance["provider"] == "misa"

    replay = await sync_misa(
        FakeMisa({None: ConnectorPage((first, invoice), None, "checkpoint-2")}),
        cursor=None,
        known_versions=known,
    )
    assert not replay.records
    assert replay.duplicates == 2


@pytest.mark.asyncio
async def test_outlook_delta_deduplicates_and_draft_is_idempotent() -> None:
    message = OutlookMessage(
        "msg-1",
        "conversation-1",
        "ap@example.com",
        ("ar@example.com",),
        "INV-1",
        "body",
        datetime(2026, 8, 24, tzinfo=UTC),
        ("attachment-1",),
    )
    fake = FakeOutlook(
        {
            None: ConnectorPage((message,), "next", "delta-1"),
            "next": ConnectorPage((message,), None, "delta-final"),
        }
    )
    result = await sync_outlook(fake, delta_link=None)
    assert result.messages == (message,)
    assert result.delta_link == "delta-final"
    assert normalize_outlook_message(message)["provider"] == "outlook"
    spec = DraftSpec(("ap@example.com",), (), "Subject", "Body")
    first = await fake.create_draft(idempotency_key="tenant:approval", spec=spec)
    second = await fake.create_draft(idempotency_key="tenant:approval", spec=spec)
    assert first == second
    assert len(fake.drafts) == 1


@pytest.mark.asyncio
async def test_zalo_dispatch_requires_approval_and_is_idempotent() -> None:
    preview = preview_zalo_notification(
        template=ZaloTemplate("reminder", 1, "vi-VN", frozenset({"case_ref"})),
        recipient=ZaloRecipient("uid", True, True),
        variables={"case_ref": "CASE-SYN"},
        now_local=__import__("datetime").time(10),
        dry_run=False,
    )
    fake = FakeZalo()
    with pytest.raises(PermissionError, match="approval"):
        await dispatch_zalo_notification(
            preview=preview, approval_status="PENDING", idempotency_key="once", adapter=fake
        )
    first = await dispatch_zalo_notification(
        preview=preview, approval_status="APPROVED", idempotency_key="once", adapter=fake
    )
    second = await dispatch_zalo_notification(
        preview=preview, approval_status="APPROVED", idempotency_key="once", adapter=fake
    )
    assert first.external_id == second.external_id
    assert len(fake.deliveries) == 1
