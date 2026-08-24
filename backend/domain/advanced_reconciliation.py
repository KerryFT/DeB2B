from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReconciliationPolicy:
    tolerance_minor: int = 0
    bank_fee_minor: int = 0
    date_window_days: int = 7
    auto_match_threshold: Decimal = Decimal("0.95")


@dataclass(frozen=True, slots=True)
class InvoiceCandidate:
    invoice_id: UUID
    invoice_number: str
    outstanding_minor: int
    due_date: date
    customer_code: str
    currency: str


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    invoice_id: UUID
    score: Decimal
    features: dict[str, Decimal]
    disposition: str


def score_candidates(
    *,
    amount_minor: int,
    booked_date: date,
    reference: str,
    currency: str,
    candidates: list[InvoiceCandidate],
    policy: ReconciliationPolicy,
) -> list[ScoredCandidate]:
    normalized = re.sub(r"[^A-Z0-9]", "", reference.upper())
    results: list[ScoredCandidate] = []
    for candidate in candidates:
        number = re.sub(r"[^A-Z0-9]", "", candidate.invoice_number.upper())
        customer = re.sub(r"[^A-Z0-9]", "", candidate.customer_code.upper())
        amount_difference = abs(candidate.outstanding_minor - amount_minor - policy.bank_fee_minor)
        features = {
            "invoice_reference": Decimal("1") if number and number in normalized else Decimal("0"),
            "customer_reference": Decimal("1")
            if customer and customer in normalized
            else Decimal("0"),
            "amount": Decimal("1") if amount_difference <= policy.tolerance_minor else Decimal("0"),
            "date": Decimal("1")
            if abs((booked_date - candidate.due_date).days) <= policy.date_window_days
            else Decimal("0"),
            "currency": Decimal("1") if currency == candidate.currency else Decimal("0"),
        }
        score = sum(
            (
                features["invoice_reference"] * Decimal("0.35"),
                features["customer_reference"] * Decimal("0.15"),
                features["amount"] * Decimal("0.30"),
                features["date"] * Decimal("0.10"),
                features["currency"] * Decimal("0.10"),
            ),
            Decimal("0"),
        )
        disposition = "AUTO_MATCH" if score >= policy.auto_match_threshold else "REVIEW"
        if currency != candidate.currency:
            disposition = "MANUAL_FX_REVIEW"
        results.append(ScoredCandidate(candidate.invoice_id, score, features, disposition))
    return sorted(results, key=lambda item: (-item.score, str(item.invoice_id)))


def validate_allocation_totals(
    *,
    transaction_amount_minor: int,
    transaction_already_allocated_minor: int,
    allocations_minor: list[int],
    bank_fee_minor: int = 0,
    tolerance_minor: int = 0,
) -> str:
    if any(amount <= 0 for amount in allocations_minor):
        raise ValueError("allocations must be positive")
    used = transaction_already_allocated_minor + sum(allocations_minor) + bank_fee_minor
    if used > transaction_amount_minor + tolerance_minor:
        raise ValueError("allocation, fee and tolerance exceed transaction")
    if used < transaction_amount_minor - tolerance_minor:
        return "PARTIAL_OR_OVERPAYMENT_REVIEW"
    return "BALANCED"
