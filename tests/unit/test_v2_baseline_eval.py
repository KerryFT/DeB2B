from tools.eval.v2_baselines import evaluate


def test_v2_baseline_release_metrics_are_reproducible_and_reconciled() -> None:
    first = evaluate()
    assert first == evaluate()
    horizons = first["probability_to_pay"]
    assert isinstance(horizons, dict)
    assert all(metric["calibration_error"] <= 0.08 for metric in horizons.values())
    cashflow = first["cashflow_30_day"]
    assert isinstance(cashflow, dict)
    assert cashflow["aggregate_wape"] <= 0.08
    assert cashflow["reconciliation_difference_minor"] == 0
