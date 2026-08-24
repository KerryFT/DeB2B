from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.application.bulk_approvals import BulkItem, preview_bulk
from backend.application.llm_analytics import LLMEvent, PricingVersion, aggregate_online
from backend.application.permissions import Permission, is_allowed
from backend.application.v1_connectors import (
    ZaloRecipient,
    ZaloTemplate,
    graph_subscription_needs_renewal,
    graph_webhook_is_new,
    preview_zalo_notification,
)
from backend.domain.advanced_reconciliation import (
    InvoiceCandidate,
    ReconciliationPolicy,
    score_candidates,
    validate_allocation_totals,
)
from backend.domain.aging_forecast import (
    ForecastInvoice,
    backtest,
    baseline_forecast,
    cashflow_buckets,
)
from backend.domain.payment_rules import (
    RuleDefinition,
    RuleScope,
    RuleType,
    detect_conflicts,
    evaluate_rules,
)


def rule(kind: RuleType, scope: RuleScope, value: dict[str, object], version: int = 1):
    return RuleDefinition(
        rule_type=kind,
        scope=scope,
        effective_from=date(2026, 1, 1),
        version=version,
        value=value,
    )


def test_permission_matrix_is_deny_by_default_and_separates_duties() -> None:
    assert is_allowed("tenant_admin", Permission.USER_MANAGE)
    assert is_allowed("approver", Permission.APPROVAL_BULK)
    assert not is_allowed("approver", Permission.RULE_PUBLISH)
    assert not is_allowed("ar_specialist", Permission.APPROVAL_BULK)
    assert not is_allowed("unknown", Permission.CASE_VIEW)


def test_customer_rules_are_deterministic_explained_and_conflict_safe() -> None:
    defaults = rule(RuleType.GRACE_PERIOD, RuleScope.DEFAULT, {"days": 1})
    customer = rule(RuleType.GRACE_PERIOD, RuleScope.CUSTOMER, {"days": 5}, version=2)
    tenant = rule(RuleType.ALLOWED_CHANNEL, RuleScope.TENANT, {"channels": ["gmail"]})
    result = evaluate_rules([defaults, customer, tenant], as_of=date(2026, 8, 24))
    assert result.values["grace_period"] == {"days": 5}
    assert result.values["allowed_channel"] == {"channels": ["gmail"]}
    assert any("v2" in explanation for explanation in result.explanation)

    conflicting = rule(RuleType.GRACE_PERIOD, RuleScope.CUSTOMER, {"days": 8}, version=3)
    assert detect_conflicts([customer, conflicting])
    with pytest.raises(ValueError, match="conflicting"):
        evaluate_rules([customer, conflicting], as_of=date(2026, 8, 24))


def test_advanced_reconciliation_explains_match_and_enforces_allocation_invariants() -> None:
    invoice_id = uuid4()
    ranked = score_candidates(
        amount_minor=995,
        booked_date=date(2026, 8, 24),
        reference="payment INV-001 CUS-A",
        currency="VND",
        candidates=[
            InvoiceCandidate(invoice_id, "INV-001", 1_000, date(2026, 8, 23), "CUS-A", "VND")
        ],
        policy=ReconciliationPolicy(bank_fee_minor=5, tolerance_minor=0),
    )
    assert ranked[0].score == Decimal("1.00")
    assert ranked[0].disposition == "AUTO_MATCH"
    assert (
        validate_allocation_totals(
            transaction_amount_minor=1_000,
            transaction_already_allocated_minor=300,
            allocations_minor=[400, 295],
            bank_fee_minor=5,
        )
        == "BALANCED"
    )
    with pytest.raises(ValueError, match="exceed"):
        validate_allocation_totals(
            transaction_amount_minor=1_000,
            transaction_already_allocated_minor=600,
            allocations_minor=[500],
        )
    fx = score_candidates(
        amount_minor=1_000,
        booked_date=date(2026, 8, 24),
        reference="INV-001",
        currency="USD",
        candidates=[InvoiceCandidate(invoice_id, "INV-001", 1_000, date(2026, 8, 24), "A", "VND")],
        policy=ReconciliationPolicy(),
    )
    assert fx[0].disposition == "MANUAL_FX_REVIEW"


def test_bulk_preview_excludes_stale_risky_and_mixed_actions() -> None:
    valid = BulkItem(uuid4(), uuid4(), 2, 2, "outlook", "ap@example.com", 100, 1)
    stale = BulkItem(uuid4(), uuid4(), 3, 2, "outlook", "ap@example.com", 200, 0)
    risky = BulkItem(uuid4(), uuid4(), 1, 1, "outlook", "ap@example.com", 300, 2, ("sensitive",))
    result = preview_bulk([valid, stale, risky])
    assert result.eligible == (valid,)
    assert result.total_minor == 100
    assert {reason for _, reason in result.excluded} == {"stale_version", "risk_review_required"}
    mixed = preview_bulk([valid, BulkItem(uuid4(), uuid4(), 1, 1, "zalo", "uid", 100, 0)])
    assert not mixed.eligible
    assert all(reason == "mixed_channel" for _, reason in mixed.excluded)


def test_zalo_preview_blocks_policy_before_external_action() -> None:
    template = ZaloTemplate("payment-reminder", 2, "vi-VN", frozenset({"case_ref"}))
    recipient = ZaloRecipient("uid-1", verified=True, consented=True)
    preview = preview_zalo_notification(
        template=template,
        recipient=recipient,
        variables={"case_ref": "CASE-SYNTHETIC"},
        now_local=time(10),
    )
    assert preview.dry_run
    with pytest.raises(PermissionError, match="quiet hours"):
        preview_zalo_notification(
            template=template,
            recipient=recipient,
            variables={"case_ref": "CASE-SYNTHETIC"},
            now_local=time(22),
        )
    with pytest.raises(PermissionError, match="eligible"):
        preview_zalo_notification(
            template=template,
            recipient=ZaloRecipient("uid-2", verified=False, consented=True),
            variables={"case_ref": "CASE-SYNTHETIC"},
            now_local=time(10),
        )


def test_outlook_webhook_deduplicates_and_subscription_renews() -> None:
    seen: set[str] = set()
    assert graph_webhook_is_new(
        client_state="secret", expected_state="secret", event_id="event-1", seen=seen
    )
    assert not graph_webhook_is_new(
        client_state="secret", expected_state="secret", event_id="event-1", seen=seen
    )
    with pytest.raises(PermissionError):
        graph_webhook_is_new(
            client_state="attacker", expected_state="secret", event_id="event-2", seen=seen
        )
    now = datetime(2026, 8, 24, tzinfo=UTC)
    assert graph_subscription_needs_renewal(now + timedelta(hours=20), now=now)
    assert not graph_subscription_needs_renewal(now + timedelta(days=2), now=now)


def test_forecast_baseline_has_uncertainty_buckets_and_reproducible_backtest() -> None:
    as_of = date(2026, 8, 24)
    invoice = ForecastInvoice("inv-1", 1_000, date(2026, 8, 20), customer_delay_days=(3, 5, 4))
    promise = ForecastInvoice("inv-2", 500, date(2026, 8, 20), promise_date=date(2026, 8, 28))
    points = baseline_forecast([invoice, promise], as_of=as_of)
    assert points[0].expected_date == date(2026, 8, 24)
    assert points[1].confidence == "HIGH"
    assert sum(cashflow_buckets(points, as_of=as_of).values()) == 1_500
    metrics = backtest(
        points,
        actual_dates={"inv-1": date(2026, 8, 25), "inv-2": date(2026, 8, 28)},
        actual_minor={"inv-1": 1_000, "inv-2": 500},
    )
    assert metrics.mae_days == 0.5
    assert metrics.wape == 0
    assert metrics.interval_coverage == 1


def test_llm_analytics_uses_effective_pricing_and_keeps_unknown_usage() -> None:
    occurred = datetime(2026, 8, 24, tzinfo=UTC)
    events = [
        LLMEvent(
            "openai",
            "model-a",
            "invoice",
            "p1",
            "primary",
            occurred,
            20,
            True,
            True,
            False,
            1_000,
            500,
        ),
        LLMEvent(
            "gemini",
            "unknown",
            "invoice",
            "p1",
            "fallback",
            occurred,
            40,
            True,
            True,
            True,
            None,
            None,
        ),
    ]
    pricing = [
        PricingVersion(
            "openai", "model-a", occurred - timedelta(days=1), "USD", Decimal("1"), Decimal("2"), 1
        ),
        PricingVersion(
            "openai",
            "model-a",
            occurred + timedelta(days=1),
            "USD",
            Decimal("999"),
            Decimal("999"),
            2,
        ),
    ]
    rows = aggregate_online(events, pricing)
    openai = next(row for row in rows if row["provider"] == "openai")
    unknown = next(row for row in rows if row["provider"] == "gemini")
    assert openai["estimated_cost"] == Decimal("0.002")
    assert unknown["estimated_cost"] is None
    assert unknown["unknown_pricing_requests"] == 1
    assert all(row["metric_kind"] == "online_operational" for row in rows)
