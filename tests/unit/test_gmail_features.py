from datetime import UTC, date, datetime, timedelta

import pytest
from cryptography.exceptions import InvalidTag

from backend.application.email_signals import extract_email_signals
from backend.application.followups import propose_follow_up
from backend.application.gmail_sync import (
    HistoryExpired,
    MessagePage,
    incremental_sync,
    initial_sync,
    notification_advances,
    should_renew_watch,
)
from backend.application.ports import DraftSpec
from backend.infrastructure.gmail_adapter import GmailDraftAdapter
from backend.infrastructure.gmail_oauth import GMAIL_SCOPES, CredentialCipher


def test_oauth_credential_is_tenant_bound_and_scopes_are_minimal() -> None:
    cipher = CredentialCipher(b"k" * 32)
    token = cipher.encrypt({"refresh_token": "secret"}, tenant_id="tenant-a")
    assert "secret" not in token
    assert cipher.decrypt(token, tenant_id="tenant-a") == {"refresh_token": "secret"}
    with pytest.raises(InvalidTag):
        cipher.decrypt(token, tenant_id="tenant-b")
    assert all("gmail.send" not in scope for scope in GMAIL_SCOPES)


@pytest.mark.asyncio
async def test_initial_pagination_and_expired_history_safe_full_sync() -> None:
    class Source:
        def __init__(self) -> None:
            self.expired = True

        async def list_page(self, *, label: str, page_token: str | None) -> MessagePage:
            assert label == "AR"
            return (
                MessagePage(("m1", "m2"), "next", "h1")
                if page_token is None
                else MessagePage(("m2", "m3"), None, "h2")
            )

        async def history(self, *, cursor: str) -> MessagePage:
            assert cursor == "old"
            raise HistoryExpired

    source = Source()
    first = await initial_sync(source, label="AR")
    assert first.message_ids == ("m1", "m2", "m3")
    assert first.next_cursor == "h2"
    recovered = await incremental_sync(source, cursor="old", label="AR")
    assert recovered.full_sync
    assert recovered.message_ids == first.message_ids


def test_watch_renewal_and_notification_order_converge() -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    assert should_renew_watch(now + timedelta(hours=23), now=now)
    assert not should_renew_watch(now + timedelta(days=3), now=now)
    assert notification_advances("100", "102")
    assert not notification_advances("102", "102")
    assert not notification_advances("102", "101")


def test_email_dispute_and_promise_signals_keep_evidence() -> None:
    signals = extract_email_signals(
        "Chúng tôi tranh chấp số tiền nhưng sẽ thanh toán phần đúng ngày 30/08/2026."
    )
    assert signals.disputed
    assert signals.promise_date == date(2026, 8, 30)
    assert "30/08/2026" in signals.evidence_quote


@pytest.mark.asyncio
async def test_gmail_adapter_is_create_only_and_preserves_recipient() -> None:
    class Execute:
        def execute(self):  # type: ignore[no-untyped-def]
            return {"id": "draft-1"}

    class Drafts:
        def create(self, **kwargs):  # type: ignore[no-untyped-def]
            assert kwargs["userId"] == "me"
            assert kwargs["body"]["message"]["raw"]
            return Execute()

    class Users:
        def drafts(self) -> Drafts:
            return Drafts()

    class Service:
        def users(self) -> Users:
            return Users()

    adapter = GmailDraftAdapter(Service(), allowed_recipients=frozenset({"ap@example.com"}))
    draft_id = await adapter.create_draft(
        idempotency_key="once",
        spec=DraftSpec(("ap@example.com",), (), "INV-1", "Evidence-backed body"),
    )
    assert draft_id == "draft-1"
    assert not hasattr(adapter, "send")
    with pytest.raises(PermissionError, match="recipient"):
        await adapter.create_draft(
            idempotency_key="wrong",
            spec=DraftSpec(("attacker@example.com",), (), "INV-1", "Body"),
        )


def test_followup_rejects_unsupported_claims() -> None:
    with pytest.raises(ValueError, match="supported"):
        propose_follow_up(
            invoice_number="INV-1", blocker="MISSING_ACCEPTANCE", supported_facts={}, version=1
        )
    proposal = propose_follow_up(
        invoice_number="INV-1",
        blocker="MISSING_ACCEPTANCE",
        supported_facts={"Số tiền": ("120.000.000 VND", "evidence-1")},
        version=2,
    )
    assert proposal.evidence_ids == ("evidence-1",)
    assert proposal.version == 2
