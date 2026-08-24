from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ThresholdMetrics:
    threshold: Decimal
    precision: Decimal
    recall: Decimal
    accepted: int


def evaluate_thresholds(
    samples: list[tuple[Decimal, bool]], thresholds: tuple[Decimal, ...]
) -> list[ThresholdMetrics]:
    positives = sum(1 for _, correct in samples if correct)
    results = []
    for threshold in thresholds:
        accepted = [(score, correct) for score, correct in samples if score >= threshold]
        true_positive = sum(1 for _, correct in accepted if correct)
        precision = Decimal(true_positive) / len(accepted) if accepted else Decimal("1")
        recall = Decimal(true_positive) / positives if positives else Decimal("1")
        results.append(ThresholdMetrics(threshold, precision, recall, len(accepted)))
    return results


def select_precision_gate(
    metrics: list[ThresholdMetrics], *, minimum_precision: Decimal
) -> ThresholdMetrics | None:
    eligible = [metric for metric in metrics if metric.precision >= minimum_precision]
    return (
        max(eligible, key=lambda metric: (metric.recall, -metric.threshold)) if eligible else None
    )
