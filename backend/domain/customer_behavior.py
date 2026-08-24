from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean, median


@dataclass(frozen=True, slots=True)
class PaymentHistory:
    invoice_id: str
    amount_minor: int
    due_date: date
    paid_date: date | None
    partial_payment_count: int = 0
    promise_count: int = 0
    broken_promise_count: int = 0
    dispute_count: int = 0
    document_friction_count: int = 0
    response_latency_hours: float | None = None
    verified_channel: str | None = None
    occurred_at: date | None = None


@dataclass(frozen=True, slots=True)
class BehaviorProfile:
    as_of: date
    window_days: int
    sample_size: int
    invoice_value_minor: int
    on_time_rate: float | None
    average_delay_days: float | None
    median_delay_days: float | None
    p90_delay_days: float | None
    payment_variability_days: float | None
    partial_payment_frequency: float | None
    broken_promise_rate: float | None
    dispute_frequency: float | None
    document_friction_rate: float | None
    average_response_latency_hours: float | None
    preferred_verified_channel: str | None
    segment: str
    data_quality: tuple[str, ...]
    provenance_invoice_ids: tuple[str, ...]


def build_behavior_profile(
    histories: list[PaymentHistory], *, as_of: date, window_days: int = 365, minimum_sample: int = 3
) -> BehaviorProfile:
    cutoff = as_of.toordinal() - window_days
    eligible = [
        item
        for item in histories
        if (item.occurred_at or item.due_date) <= as_of
        and (item.occurred_at or item.due_date).toordinal() >= cutoff
    ]
    paid = [item for item in eligible if item.paid_date is not None and item.paid_date <= as_of]
    delays = sorted(
        max(0, (item.paid_date - item.due_date).days) for item in paid if item.paid_date
    )
    data_quality: list[str] = []
    if len(eligible) < minimum_sample:
        data_quality.append("insufficient_sample")
    if len(paid) < len(eligible):
        data_quality.append("open_or_censored_invoices")
    variability = None
    if delays:
        center = mean(delays)
        variability = mean(abs(delay - center) for delay in delays)
    channels = [item.verified_channel for item in eligible if item.verified_channel]
    preferred = max(set(channels), key=channels.count) if channels else None
    if len(eligible) < minimum_sample:
        segment = "insufficient_data"
    elif (variability or 0) <= 5 and (mean(delays) if delays else 0) <= 7:
        segment = "consistent"
    else:
        segment = "variable"
    sample = len(eligible)
    promises = sum(item.promise_count for item in eligible)
    response = [
        item.response_latency_hours for item in eligible if item.response_latency_hours is not None
    ]
    return BehaviorProfile(
        as_of,
        window_days,
        sample,
        sum(item.amount_minor for item in eligible),
        sum((item.paid_date or as_of) <= item.due_date for item in paid) / len(paid)
        if paid
        else None,
        mean(delays) if delays else None,
        median(delays) if delays else None,
        float(delays[min(len(delays) - 1, int(0.9 * len(delays)))]) if delays else None,
        variability,
        sum(item.partial_payment_count > 0 for item in eligible) / sample if sample else None,
        sum(item.broken_promise_count for item in eligible) / promises if promises else None,
        sum(item.dispute_count > 0 for item in eligible) / sample if sample else None,
        sum(item.document_friction_count > 0 for item in eligible) / sample if sample else None,
        mean(response) if response else None,
        preferred,
        segment,
        tuple(data_quality),
        tuple(item.invoice_id for item in eligible),
    )
