from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow


@dataclass
class CaseWorkflowInput:
    tenant_id: str
    case_id: str
    status: str = "IMPORTED"
    promise_timeout_days: int = 30


@workflow.defn
class PaymentCaseWorkflow:
    def __init__(self) -> None:
        self.status = "IMPORTED"
        self.pending_events: list[str] = []
        self.cancelled = False

    @workflow.run
    async def run(self, request: CaseWorkflowInput) -> str:
        self.status = request.status
        while not self.cancelled and self.status not in {"PAID", "CLOSED", "CANCELLED"}:
            try:
                await workflow.wait_condition(
                    lambda: bool(self.pending_events) or self.cancelled,
                    timeout=timedelta(days=request.promise_timeout_days),
                )
            except TimeoutError:
                self.status = "OVERDUE"
                continue
            if self.cancelled:
                self.status = "CANCELLED"
                break
            if self.pending_events:
                self.status = self.pending_events.pop(0)
        return self.status

    @workflow.signal
    async def transition(self, status: str) -> None:
        self.pending_events.append(status)

    @workflow.signal
    async def cancel(self) -> None:
        self.cancelled = True

    @workflow.query
    def current_status(self) -> str:
        return self.status
