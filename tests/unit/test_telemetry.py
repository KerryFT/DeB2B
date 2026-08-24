from prometheus_client import generate_latest

from backend.infrastructure.telemetry import record_operational_failure


def test_operational_failure_metric_has_bounded_labels() -> None:
    record_operational_failure(boundary="unexpected-tenant-value", error=TimeoutError())
    metrics = generate_latest().decode()
    assert 'ar_operation_failures_total{boundary="other",error_class="TimeoutError"}' in metrics
