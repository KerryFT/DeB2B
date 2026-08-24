from unittest.mock import Mock
from uuid import uuid4

from backend.application.failure_queue import mark_recovered, record_failure
from tools.load_profile import model_capacity


def test_failure_queue_backs_off_dead_letters_and_recovers() -> None:
    session = Mock()
    retry = record_failure(
        session,
        tenant_id=uuid4(),
        operation="gmail.sync",
        payload={"cursor": "1"},
        error=TimeoutError(),
        attempts=2,
    )
    assert retry.status == "PENDING_RETRY"
    assert retry.next_retry_at is not None
    dead = record_failure(
        session,
        tenant_id=uuid4(),
        operation="gmail.sync",
        payload={},
        error=TimeoutError(),
        attempts=5,
    )
    assert dead.status == "DEAD_LETTER"
    mark_recovered(dead)
    assert dead.status == "RECOVERED"


def test_5k_month_capacity_has_bounded_worker_estimate() -> None:
    report = model_capacity()
    assert report.monthly_cases == 5_000
    assert report.required_workers_at_30s <= 2
