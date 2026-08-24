from datetime import date
from decimal import Decimal

from backend.domain.calibration import evaluate_thresholds, select_precision_gate
from backend.domain.matching import MatchFeatures, score_features


def test_threshold_selection_prefers_recall_after_precision_gate() -> None:
    samples = [
        (Decimal("0.99"), True),
        (Decimal("0.90"), True),
        (Decimal("0.75"), False),
        (Decimal("0.70"), True),
    ]
    metrics = evaluate_thresholds(samples, (Decimal("0.7"), Decimal("0.8"), Decimal("0.95")))
    selected = select_precision_gate(metrics, minimum_precision=Decimal("0.95"))
    assert selected is not None
    assert selected.threshold == Decimal("0.8")
    assert selected.precision == Decimal("1")


def test_full_feature_score_is_explained() -> None:
    observed = MatchFeatures(
        invoice_number="INV-2026-001O",
        amount_minor=100_000_050,
        customer_tax_id="SYN-1",
        po_number="PO-9",
        issue_date=date(2026, 8, 1),
    )
    expected = MatchFeatures(
        invoice_number="INV-2026-0010",
        amount_minor=100_000_000,
        customer_tax_id="syn-1",
        po_number="PO-9",
        issue_date=date(2026, 8, 2),
    )
    score, reasons = score_features(observed, expected)
    assert score >= Decimal("0.6")
    assert "fuzzy_invoice_number" in reasons
    assert "amount_within_tolerance" in reasons
    assert "exact_customer_tax_id" in reasons
