from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean


@dataclass(frozen=True, slots=True)
class ForecastInvoice:
    invoice_id: str
    outstanding_minor: int
    due_date: date
    promise_date: date | None = None
    customer_delay_days: tuple[int, ...] = ()
    promise_broken: bool = False


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    invoice_id: str
    contractual_date: date
    expected_date: date
    expected_minor: int
    low_minor: int
    high_minor: int
    confidence: str
    provenance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    mae_days: float
    wape: float
    bias_days: float
    interval_coverage: float


def baseline_forecast(invoices: list[ForecastInvoice], *, as_of: date) -> list[ForecastPoint]:
    points: list[ForecastPoint] = []
    for invoice in invoices:
        history = tuple(delay for delay in invoice.customer_delay_days if delay >= -365)
        average_delay = round(mean(history)) if history else 0
        provenance = ["invoice_due_date"]
        expected = invoice.due_date + timedelta(days=average_delay)
        confidence = "MEDIUM" if len(history) >= 3 else "LOW"
        spread = (
            max(7, round(mean(abs(item - average_delay) for item in history))) if history else 14
        )
        if invoice.promise_date is not None and not invoice.promise_broken:
            expected = invoice.promise_date
            provenance.append("active_promise_to_pay")
            confidence = "HIGH"
            spread = 3
        elif invoice.promise_broken:
            expected += timedelta(days=7)
            provenance.append("broken_promise_penalty")
            confidence = "LOW"
            spread = max(spread, 14)
        expected = max(expected, as_of)
        points.append(
            ForecastPoint(
                invoice.invoice_id,
                invoice.due_date,
                expected,
                invoice.outstanding_minor,
                max(0, round(invoice.outstanding_minor * (0.8 if confidence == "LOW" else 0.95))),
                invoice.outstanding_minor,
                confidence,
                tuple(provenance),
            )
        )
    return points


def cashflow_buckets(
    points: list[ForecastPoint], *, as_of: date, bucket_days: int = 7
) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for point in points:
        bucket = max(0, (point.expected_date - as_of).days // bucket_days)
        label = f"{bucket * bucket_days}-{(bucket + 1) * bucket_days - 1}d"
        buckets[label] = buckets.get(label, 0) + point.expected_minor
    return buckets


def backtest(
    predictions: list[ForecastPoint], *, actual_dates: dict[str, date], actual_minor: dict[str, int]
) -> BacktestMetrics:
    comparable = [item for item in predictions if item.invoice_id in actual_dates]
    if not comparable:
        raise ValueError("backtest requires actual outcomes")
    errors = [(item.expected_date - actual_dates[item.invoice_id]).days for item in comparable]
    amount_error = sum(
        abs(item.expected_minor - actual_minor.get(item.invoice_id, 0)) for item in comparable
    )
    actual_total = sum(actual_minor.get(item.invoice_id, 0) for item in comparable)
    coverage = sum(
        item.low_minor <= actual_minor.get(item.invoice_id, 0) <= item.high_minor
        for item in comparable
    ) / len(comparable)
    return BacktestMetrics(
        mae_days=mean(abs(error) for error in errors),
        wape=amount_error / actual_total if actual_total else 0.0,
        bias_days=mean(errors),
        interval_coverage=coverage,
    )
