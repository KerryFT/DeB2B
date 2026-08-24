from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.application.ports import DraftSpec
from backend.domain.email_automation import AutomationDecision


class EmailSendPort(Protocol):
    async def send_approved(
        self, *, idempotency_key: str, spec: DraftSpec, policy_version: str
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    status: str
    external_id: str | None


async def deliver_automated_email(
    *,
    decision: AutomationDecision,
    spec: DraftSpec,
    adapter: EmailSendPort,
    external_delivery_enabled: bool,
) -> DeliveryResult:
    if decision.disposition != "ENQUEUE" or not decision.eligible:
        raise PermissionError("automation decision is not dispatchable")
    if not external_delivery_enabled:
        return DeliveryResult("DELIVERY_DISABLED", None)
    external_id = await adapter.send_approved(
        idempotency_key=decision.idempotency_key,
        spec=spec,
        policy_version=decision.policy_version,
    )
    return DeliveryResult("SENT", external_id)
