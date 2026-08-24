from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean

HORIZONS = (7, 14, 30)


@dataclass(frozen=True, slots=True)
class PaymentOutcome:
    entity_id: str
    segment: str
    as_of: date
    paid_at: date | None
    observation_cutoff: date


@dataclass(frozen=True, slots=True)
class ProbabilityPrediction:
    entity_id: str
    as_of: date
    model_version: str
    probabilities: dict[int, float]
    reason_codes: tuple[str, ...]
    data_quality: tuple[str, ...]
    feature_snapshot_hash: str


@dataclass(frozen=True, slots=True)
class ProbabilityMetrics:
    brier_score: float
    log_loss: float
    calibration_error: float
    positive_rate: float


def horizon_label(outcome: PaymentOutcome, horizon_days: int) -> int | None:
    horizon_end = outcome.as_of + timedelta(days=horizon_days)
    if horizon_end > outcome.observation_cutoff:
        return None
    return int(outcome.paid_at is not None and outcome.as_of < outcome.paid_at <= horizon_end)


def fit_segment_baseline(
    outcomes: list[PaymentOutcome], *, horizon_days: int, smoothing: float = 1.0
) -> dict[str, float]:
    grouped: dict[str, list[int]] = {}
    for outcome in outcomes:
        label = horizon_label(outcome, horizon_days)
        if label is not None:
            grouped.setdefault(outcome.segment, []).append(label)
    return {
        segment: (sum(labels) + smoothing) / (len(labels) + 2 * smoothing)
        for segment, labels in grouped.items()
    }


def predict_probability(
    *,
    entity_id: str,
    segment: str,
    as_of: date,
    rates_by_horizon: dict[int, dict[str, float]],
    feature_snapshot_hash: str,
    active_promise: bool = False,
    disputed: bool = False,
    sparse: bool = False,
) -> ProbabilityPrediction:
    probabilities: dict[int, float] = {}
    reasons = [f"segment:{segment}"]
    quality: list[str] = []
    previous = 0.0
    for horizon in HORIZONS:
        rate = rates_by_horizon.get(horizon, {}).get(segment, 0.5)
        if active_promise:
            rate = min(0.98, rate + 0.15)
        if disputed:
            rate = max(0.01, rate - 0.25)
        rate = max(previous, rate)
        probabilities[horizon] = round(rate, 6)
        previous = rate
    if active_promise:
        reasons.append("active_promise")
    if disputed:
        reasons.append("active_dispute")
    if sparse:
        quality.append("insufficient_history")
    return ProbabilityPrediction(
        entity_id,
        as_of,
        "segment-beta-baseline-v1",
        probabilities,
        tuple(reasons),
        tuple(quality),
        feature_snapshot_hash,
    )


def calibration_metrics(
    probabilities: list[float], labels: list[int], *, bins: int = 10
) -> ProbabilityMetrics:
    if not probabilities or len(probabilities) != len(labels):
        raise ValueError("aligned non-empty predictions and labels are required")
    clipped = [min(1 - 1e-9, max(1e-9, value)) for value in probabilities]
    brier = mean(
        (probability - label) ** 2 for probability, label in zip(clipped, labels, strict=True)
    )
    log_loss = -mean(
        label * math.log(probability) + (1 - label) * math.log(1 - probability)
        for probability, label in zip(clipped, labels, strict=True)
    )
    calibration_error = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        members = [
            position
            for position, probability in enumerate(clipped)
            if low <= probability < high or (index == bins - 1 and probability == 1)
        ]
        if members:
            predicted = mean(clipped[position] for position in members)
            observed = mean(labels[position] for position in members)
            calibration_error += len(members) / len(labels) * abs(predicted - observed)
    return ProbabilityMetrics(brier, log_loss, calibration_error, mean(labels))
