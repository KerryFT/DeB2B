from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from backend.domain.account_manager_benchmark import ManagerCaseOutcome, benchmark_managers
from backend.domain.cashflow_forecast_v2 import (
    CashFlowInput,
    aggregate_by_currency,
    backtest_cashflow,
    probabilistic_cashflow,
)
from backend.domain.customer_behavior import PaymentHistory, build_behavior_profile
from backend.domain.dispute_root_causes import (
    RootCause,
    assess_root_cause,
    correct_assessment,
    reopen_assessment,
    resolve_assessment,
)
from backend.domain.email_automation import (
    AutomationCandidate,
    AutomationMode,
    AutomationPolicy,
    evaluate_automation,
    revalidate_before_send,
)
from backend.domain.escalation import EscalationInput, EscalationStrategy, recommend_escalation
from backend.domain.feature_governance import (
    FeatureEvent,
    ModelCandidate,
    build_point_in_time_snapshot,
    choose_champion,
)
from backend.domain.probability_to_pay import (
    PaymentOutcome,
    calibration_metrics,
    fit_segment_baseline,
    horizon_label,
    predict_probability,
)

NOW = datetime(2026, 8, 24, 10, tzinfo=UTC)


def candidate(**changes: object) -> AutomationCandidate:
    base = AutomationCandidate(
        "tenant-a",
        "case-a",
        2,
        1_000_000,
        5,
        False,
        False,
        False,
        False,
        False,
        "ap@customer.test",
        True,
        False,
        False,
        True,
        True,
        False,
        True,
        10,
        0.01,
        True,
        0,
        None,
        NOW,
    )
    return replace(base, **changes)


def enabled_policy(**changes: object) -> AutomationPolicy:
    return replace(
        AutomationPolicy(
            mode=AutomationMode.ENABLED,
            tenant_kill_switch=False,
            canary_percent=100,
        ),
        **changes,
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"paid": True}, "already_paid"),
        ({"disputed": True}, "active_dispute"),
        ({"recipient": "evil@test", "recipient_verified": False}, "unverified_recipient"),
        ({"recipient_suppressed": True}, "suppressed_recipient"),
        ({"manual_review": True}, "manual_review"),
        ({"template_has_forbidden_language": True}, "forbidden_language"),
    ],
)
def test_auto_send_safety_critical_cases_are_blocked(
    changes: dict[str, object], reason: str
) -> None:
    decision = evaluate_automation(candidate(**changes), enabled_policy(), global_kill_switch=False)
    assert not decision.eligible
    assert decision.disposition == "BLOCKED"
    assert reason in decision.exclusions


def test_auto_send_defaults_and_kill_switch_cannot_dispatch() -> None:
    default = evaluate_automation(candidate(), AutomationPolicy())
    killed = evaluate_automation(candidate(), enabled_policy(), global_kill_switch=True)
    assert default.disposition == killed.disposition == "BLOCKED"
    assert "automation_disabled" in default.exclusions
    assert "kill_switch_active" in killed.exclusions


def test_shadow_never_enqueues_and_duplicate_key_is_stable() -> None:
    policy = enabled_policy(mode=AutomationMode.SHADOW)
    first = evaluate_automation(candidate(), policy, global_kill_switch=False)
    second = evaluate_automation(candidate(), policy, global_kill_switch=False)
    assert first.disposition == "SHADOW_ELIGIBLE"
    assert first.idempotency_key == second.idempotency_key
    assert first.disposition != "ENQUEUE"


def test_pre_send_revalidation_blocks_stale_state_and_recipient_change() -> None:
    original = candidate()
    stale = revalidate_before_send(
        original,
        replace(original, case_version=3),
        enabled_policy(),
        global_kill_switch=False,
    )
    changed = revalidate_before_send(
        original,
        replace(original, recipient="wrong@test"),
        enabled_policy(),
        global_kill_switch=False,
    )
    assert stale.exclusions == ("stale_case_version",)
    assert changed.exclusions == ("recipient_changed",)


def test_point_in_time_snapshot_excludes_future_and_is_reproducible() -> None:
    events = [
        FeatureEvent("old", NOW - timedelta(days=1), {"amount": 10}),
        FeatureEvent("future", NOW + timedelta(seconds=1), {"amount": 99}),
    ]
    first = build_point_in_time_snapshot(
        entity_type="invoice",
        entity_id="invoice-1",
        as_of=NOW,
        feature_version="v1",
        events=events,
    )
    second = build_point_in_time_snapshot(
        entity_type="invoice",
        entity_id="invoice-1",
        as_of=NOW,
        feature_version="v1",
        events=list(reversed(events)),
    )
    assert first.provenance_event_ids == ("old",)
    assert first.inputs_hash == second.inputs_hash
    assert "future" not in first.provenance_event_ids


def test_model_champion_requires_recorded_minimum_improvement() -> None:
    baseline = ModelCandidate("baseline", "v1", 0.21, NOW, "dataset-v1")
    marginal = ModelCandidate("marginal", "v2", 0.205, NOW, "dataset-v1")
    challenger = ModelCandidate("better", "v3", 0.18, NOW, "dataset-v1")
    assert (
        choose_champion(baseline, [marginal], lower_is_better=True, minimum_improvement=0.01)
        == baseline
    )
    assert (
        choose_champion(baseline, [challenger], lower_is_better=True, minimum_improvement=0.01)
        == challenger
    )


def test_dispute_unknown_without_evidence_and_human_lifecycle() -> None:
    unknown = assess_root_cause(reason_codes=["amount_mismatch"], evidence_ids=[], detected_at=NOW)
    assert unknown.primary == RootCause.UNKNOWN
    assessed = assess_root_cause(
        reason_codes=["amount_mismatch", "po_mismatch"],
        evidence_ids=["span-1"],
        detected_at=NOW,
    )
    corrected = correct_assessment(
        assessed, primary=RootCause.PO_MISMATCH, contributing=(RootCause.PRICING_AMOUNT_MISMATCH,)
    )
    resolved = resolve_assessment(corrected, resolution="Correct PO supplied", resolved_at=NOW)
    reopened = reopen_assessment(resolved)
    assert corrected.human_corrected
    assert reopened.status == "OPEN" and reopened.reopen_count == 1


def test_behavior_profile_ignores_late_future_events_and_uses_neutral_label() -> None:
    histories = [
        PaymentHistory("a", 100, date(2026, 8, 1), date(2026, 8, 2), occurred_at=date(2026, 7, 1)),
        PaymentHistory("future", 100, date(2026, 9, 1), None, occurred_at=date(2026, 9, 1)),
    ]
    profile = build_behavior_profile(histories, as_of=date(2026, 8, 24), minimum_sample=3)
    assert profile.provenance_invoice_ids == ("a",)
    assert profile.segment == "insufficient_data"
    assert "insufficient_sample" in profile.data_quality


def test_probability_labels_handle_censoring_and_predictions_are_monotonic() -> None:
    censored = PaymentOutcome("i1", "s", date(2026, 8, 1), None, date(2026, 8, 10))
    observed = PaymentOutcome("i2", "s", date(2026, 8, 1), date(2026, 8, 5), date(2026, 9, 1))
    assert horizon_label(censored, 14) is None
    assert horizon_label(observed, 7) == 1
    rates = {
        horizon: fit_segment_baseline([observed], horizon_days=horizon) for horizon in (7, 14, 30)
    }
    prediction = predict_probability(
        entity_id="i2",
        segment="s",
        as_of=date(2026, 8, 1),
        rates_by_horizon=rates,
        feature_snapshot_hash="hash",
    )
    values = list(prediction.probabilities.values())
    assert values == sorted(values)


def test_probability_calibration_metrics_are_finite() -> None:
    metrics = calibration_metrics([0.1, 0.8, 0.7, 0.2], [0, 1, 1, 0])
    assert 0 <= metrics.brier_score < 0.1
    assert metrics.log_loss > 0
    assert 0 <= metrics.calibration_error <= 1


def test_cashflow_reconciles_and_rejects_duplicate_invoice() -> None:
    item = CashFlowInput("i1", "c1", "m1", "VND", 1_000, date(2026, 8, 1), {30: 0.7})
    components = probabilistic_cashflow([item], horizon_days=30)
    totals = aggregate_by_currency(components)["VND"]
    assert totals["contractual"] == 1_000
    assert totals["p10"] <= totals["p50"] <= totals["p90"]
    with pytest.raises(ValueError, match="double-count"):
        probabilistic_cashflow([item, item], horizon_days=30)


def test_cashflow_backtest_reports_error_and_interval_coverage() -> None:
    item = CashFlowInput("i1", "c1", "m1", "VND", 1_000, date(2026, 8, 1), {30: 0.7})
    component = probabilistic_cashflow([item], horizon_days=30)
    metrics = backtest_cashflow(component, actual_by_invoice={"i1": 700})
    assert metrics.wape == 0
    assert metrics.bias == 0
    assert metrics.interval_coverage == 1


def test_escalation_is_evidence_backed_and_never_executes_legal_action() -> None:
    recommendations = recommend_escalation(
        EscalationInput(date(2026, 8, 24), 45, 100, None, True, False, 0, 0, ("span-1",))
    )
    assert all(item.evidence_ids for item in recommendations)
    assert all("human_acceptance" in item.prerequisites for item in recommendations)
    assert EscalationStrategy.LEGAL_REVIEW_REFERRAL not in {
        item.strategy for item in recommendations
    }


def test_benchmark_suppresses_small_cohort_and_adjusts_portfolio() -> None:
    small = benchmark_managers(
        [ManagerCaseOutcome("c1", "m1", 4, 1, None, 2, 0.5, 1)], minimum_sample=3
    )[0]
    assert small.suppressed and not small.case_ids
    outcomes = [
        ManagerCaseOutcome(f"c{i}", "m1", 4 + i, 1, None, 2, 0.5, 1 + i / 10) for i in range(3)
    ]
    row = benchmark_managers(outcomes, minimum_sample=3)[0]
    assert not row.suppressed
    assert row.raw_timeliness != row.adjusted_timeliness


def test_benchmark_rejects_invalid_attribution() -> None:
    with pytest.raises(ValueError, match="attribution"):
        benchmark_managers(
            [ManagerCaseOutcome("c1", "m1", 1, 1, None, 1, 1, 1, attribution_share=0)]
        )
