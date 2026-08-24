from __future__ import annotations

from prometheus_client import Counter, Gauge

OPERATION_FAILURES = Counter(
    "ar_operation_failures_total",
    "Failures at controlled external-operation boundaries",
    ["boundary", "error_class"],
)
CONNECTOR_STALENESS = Gauge(
    "ar_connector_staleness_seconds",
    "Seconds since the connector cursor was committed",
    ["provider"],
)
WORKFLOW_BACKLOG = Gauge(
    "ar_workflow_backlog",
    "Payment case workflows awaiting a worker",
    ["task_queue"],
)


def record_operational_failure(*, boundary: str, error: Exception) -> None:
    allowed = {"gmail", "llm", "ocr", "storage", "workflow"}
    normalized = boundary if boundary in allowed else "other"
    OPERATION_FAILURES.labels(normalized, type(error).__name__).inc()
