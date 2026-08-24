import asyncio
from datetime import timedelta

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from backend.workflows.payment_case import CaseWorkflowInput, PaymentCaseWorkflow


@pytest.mark.asyncio
async def test_workflow_accepts_signal_and_completes() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue="test", workflows=[PaymentCaseWorkflow]):
            handle = await env.client.start_workflow(
                PaymentCaseWorkflow.run,
                CaseWorkflowInput("tenant", "case"),
                id="tenant/case",
                task_queue="test",
            )
            await handle.signal(PaymentCaseWorkflow.transition, "PAID")
            assert await handle.result() == "PAID"


@pytest.mark.asyncio
async def test_workflow_timer_survives_virtual_month() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue="test-timer", workflows=[PaymentCaseWorkflow]):
            handle = await env.client.start_workflow(
                PaymentCaseWorkflow.run,
                CaseWorkflowInput("tenant", "case-timer"),
                id="tenant/case-timer",
                task_queue="test-timer",
            )
            assert await handle.query(PaymentCaseWorkflow.current_status) == "IMPORTED"
            await env.sleep(timedelta(days=31))
            # Let the worker consume the fired virtual timer before querying state.
            await asyncio.sleep(0.1)
            assert await handle.query(PaymentCaseWorkflow.current_status) == "OVERDUE"
            await handle.signal(PaymentCaseWorkflow.cancel)
            assert await handle.result() == "CANCELLED"


@pytest.mark.asyncio
async def test_promise_due_timer_becomes_overdue() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue="test-promise", workflows=[PaymentCaseWorkflow]):
            handle = await env.client.start_workflow(
                PaymentCaseWorkflow.run,
                CaseWorkflowInput(
                    "tenant", "case-promise", status="PROMISE_TO_PAY", promise_timeout_days=1
                ),
                id="tenant/case-promise",
                task_queue="test-promise",
            )
            await env.sleep(timedelta(days=2))
            await asyncio.sleep(0.1)
            assert await handle.query(PaymentCaseWorkflow.current_status) == "OVERDUE"
            await handle.signal(PaymentCaseWorkflow.cancel)
            assert await handle.result() == "CANCELLED"
