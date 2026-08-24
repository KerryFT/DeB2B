import pytest

from backend.application.email_delivery import deliver_automated_email
from backend.application.ports import DraftSpec
from backend.domain.email_automation import AutomationDecision
from backend.infrastructure.v1_fakes import FakeEmailSender


@pytest.mark.asyncio
async def test_external_delivery_lock_prevents_adapter_call() -> None:
    adapter = FakeEmailSender()
    result = await deliver_automated_email(
        decision=AutomationDecision(True, "ENQUEUE", (), "policy-v1", "tenant:case:v1"),
        spec=DraftSpec(("verified@example.test",), (), "Reminder", "Approved template"),
        adapter=adapter,
        external_delivery_enabled=False,
    )
    assert result.status == "DELIVERY_DISABLED"
    assert result.external_id is None
    assert adapter.calls == 0


@pytest.mark.asyncio
async def test_fake_email_adapter_is_idempotent_for_same_decision_key() -> None:
    adapter = FakeEmailSender()
    decision = AutomationDecision(True, "ENQUEUE", (), "policy-v1", "tenant:case:v1")
    spec = DraftSpec(("verified@example.test",), (), "Reminder", "Approved template")
    first = await deliver_automated_email(
        decision=decision, spec=spec, adapter=adapter, external_delivery_enabled=True
    )
    second = await deliver_automated_email(
        decision=decision, spec=spec, adapter=adapter, external_delivery_enabled=True
    )
    assert first.external_id == second.external_id
    assert len(adapter.deliveries) == 1


@pytest.mark.asyncio
async def test_blocked_decision_cannot_reach_provider() -> None:
    adapter = FakeEmailSender()
    with pytest.raises(PermissionError, match="not dispatchable"):
        await deliver_automated_email(
            decision=AutomationDecision(False, "BLOCKED", ("active_dispute",), "v1", "key"),
            spec=DraftSpec(("verified@example.test",), (), "Reminder", "Body"),
            adapter=adapter,
            external_delivery_enabled=True,
        )
    assert adapter.calls == 0
