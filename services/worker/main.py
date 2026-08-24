import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from backend.infrastructure.config import get_settings
from backend.workflows.payment_case import PaymentCaseWorkflow


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_target, namespace=settings.temporal_namespace)
    worker = Worker(
        client, task_queue=settings.temporal_task_queue, workflows=[PaymentCaseWorkflow]
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
