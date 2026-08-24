from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from backend.domain.cashflow_forecast_v2 import (
    CashFlowInput,
    backtest_cashflow,
    probabilistic_cashflow,
)
from backend.domain.probability_to_pay import (
    HORIZONS,
    PaymentOutcome,
    calibration_metrics,
    fit_segment_baseline,
    horizon_label,
    predict_probability,
)

SEED = 20260824
OFFSETS = {
    "consistent": (3, 5, 7, 10, 12, 14, 20, None),
    "variable": (5, 10, 16, 25, None, None, None, None),
}


def outcomes(split: str, start: date) -> list[PaymentOutcome]:
    rows: list[PaymentOutcome] = []
    for segment, offsets in OFFSETS.items():
        for index in range(24):
            as_of = start + timedelta(days=index)
            offset = offsets[index % len(offsets)]
            rows.append(
                PaymentOutcome(
                    f"{split}-{segment}-{index}",
                    segment,
                    as_of,
                    as_of + timedelta(days=offset) if offset is not None else None,
                    as_of + timedelta(days=45),
                )
            )
    return rows


def evaluate() -> dict[str, object]:
    train = outcomes("train", date(2025, 1, 1))
    test = outcomes("test", date(2025, 7, 1))
    rates = {horizon: fit_segment_baseline(train, horizon_days=horizon) for horizon in HORIZONS}
    probability_metrics: dict[str, object] = {}
    predictions_30: dict[str, float] = {}
    for horizon in HORIZONS:
        probabilities: list[float] = []
        labels: list[int] = []
        for row in test:
            label = horizon_label(row, horizon)
            if label is None:
                continue
            prediction = predict_probability(
                entity_id=row.entity_id,
                segment=row.segment,
                as_of=row.as_of,
                rates_by_horizon=rates,
                feature_snapshot_hash=f"synthetic:{row.entity_id}:{row.as_of}",
            )
            probabilities.append(prediction.probabilities[horizon])
            labels.append(label)
            if horizon == 30:
                predictions_30[row.entity_id] = prediction.probabilities[horizon]
        metric = calibration_metrics(probabilities, labels)
        probability_metrics[str(horizon)] = {
            "brier_score": round(metric.brier_score, 6),
            "log_loss": round(metric.log_loss, 6),
            "calibration_error": round(metric.calibration_error, 6),
            "positive_rate": round(metric.positive_rate, 6),
            "sample_count": len(labels),
        }
    forecast_inputs = [
        CashFlowInput(
            row.entity_id,
            row.segment,
            "synthetic-owner",
            "VND",
            1_000_000,
            row.as_of,
            {30: predictions_30[row.entity_id]},
        )
        for row in test
    ]
    components = probabilistic_cashflow(forecast_inputs, horizon_days=30)
    actual = {row.entity_id: 1_000_000 if horizon_label(row, 30) == 1 else 0 for row in test}
    forecast_metric = backtest_cashflow(components, actual_by_invoice=actual)
    actual_total = sum(actual.values())
    predicted_total = sum(item.p50_minor for item in components)
    return {
        "artifact_version": "v2-baselines-v1",
        "seed": SEED,
        "dataset_version": "synthetic-v3",
        "split": {
            "train_start": "2025-01-01",
            "test_start": "2025-07-01",
            "observation_days": 45,
            "train_samples": len(train),
            "test_samples": len(test),
        },
        "champion": "segment-beta-baseline-v1",
        "probability_to_pay": probability_metrics,
        "cashflow_30_day": {
            "invoice_wape": round(forecast_metric.wape, 6),
            "bias": round(forecast_metric.bias, 6),
            "interval_coverage": round(forecast_metric.interval_coverage, 6),
            "aggregate_wape": round(abs(predicted_total - actual_total) / actual_total, 6),
            "reconciliation_difference_minor": sum(item.contractual_minor for item in components)
            - sum(item.outstanding_minor for item in forecast_inputs),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
