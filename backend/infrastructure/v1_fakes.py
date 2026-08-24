from __future__ import annotations

from backend.application.ports import DraftSpec
from backend.application.v1_connectors import (
    ConnectorPage,
    MisaRecord,
    OutlookMessage,
    RetryableConnectorError,
    ZaloPreview,
)


class FakeMisa:
    def __init__(
        self,
        pages: dict[str | None, ConnectorPage[MisaRecord]],
        *,
        throttle_once: bool = False,
    ) -> None:
        self.pages = pages
        self.throttle_once = throttle_once
        self.calls = 0

    async def fetch(self, *, cursor: str | None) -> ConnectorPage[MisaRecord]:
        self.calls += 1
        if self.throttle_once:
            self.throttle_once = False
            raise RetryableConnectorError("throttled", retry_after_seconds=0)
        return self.pages[cursor]


class FakeOutlook:
    def __init__(self, pages: dict[str | None, ConnectorPage[OutlookMessage]]) -> None:
        self.pages = pages
        self.drafts: dict[str, str] = {}

    async def delta(self, *, delta_link: str | None) -> ConnectorPage[OutlookMessage]:
        return self.pages[delta_link]

    async def create_draft(self, *, idempotency_key: str, spec: DraftSpec) -> str:
        del spec
        return self.drafts.setdefault(idempotency_key, f"outlook-draft-{len(self.drafts) + 1}")


class FakeEmailSender:
    def __init__(self) -> None:
        self.deliveries: dict[str, str] = {}
        self.calls = 0

    async def send_approved(
        self, *, idempotency_key: str, spec: DraftSpec, policy_version: str
    ) -> str:
        del spec, policy_version
        self.calls += 1
        return self.deliveries.setdefault(idempotency_key, f"fake-email-{len(self.deliveries) + 1}")


class FakeZalo:
    def __init__(self, *, outcome: str = "success") -> None:
        self.outcome = outcome
        self.deliveries: dict[str, str] = {}

    async def deliver(self, *, idempotency_key: str, preview: ZaloPreview) -> str:
        del preview
        if self.outcome == "reject":
            raise PermissionError("fake provider rejected template")
        if self.outcome == "timeout":
            raise TimeoutError("fake provider timeout")
        return self.deliveries.setdefault(
            idempotency_key, f"zalo-receipt-{len(self.deliveries) + 1}"
        )
