from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    invoice_id: UUID
    score: Decimal
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchFeatures:
    invoice_number: str | None = None
    amount_minor: int | None = None
    customer_tax_id: str | None = None
    po_number: str | None = None
    issue_date: date | None = None


def score_features(
    observed: MatchFeatures, expected: MatchFeatures
) -> tuple[Decimal, tuple[str, ...]]:
    score = Decimal("0")
    reasons = []
    if observed.invoice_number and expected.invoice_number:
        similarity = Decimal(
            str(
                round(
                    SequenceMatcher(
                        None, observed.invoice_number.casefold(), expected.invoice_number.casefold()
                    ).ratio(),
                    4,
                )
            )
        )
        if similarity == 1:
            score += Decimal("0.45")
            reasons.append("exact_invoice_number")
        elif similarity >= Decimal("0.90"):
            score += Decimal("0.25")
            reasons.append("fuzzy_invoice_number")
    if observed.amount_minor is not None and expected.amount_minor is not None:
        difference = abs(observed.amount_minor - expected.amount_minor)
        tolerance = max(1, round(expected.amount_minor * 0.001))
        if difference == 0:
            score += Decimal("0.30")
            reasons.append("exact_amount")
        elif difference <= tolerance:
            score += Decimal("0.15")
            reasons.append("amount_within_tolerance")
    if (
        observed.customer_tax_id
        and expected.customer_tax_id
        and observed.customer_tax_id.casefold() == expected.customer_tax_id.casefold()
    ):
        score += Decimal("0.15")
        reasons.append("exact_customer_tax_id")
    if observed.po_number and expected.po_number and observed.po_number == expected.po_number:
        score += Decimal("0.05")
        reasons.append("exact_po_number")
    if observed.issue_date and expected.issue_date:
        days = abs((observed.issue_date - expected.issue_date).days)
        if days == 0:
            score += Decimal("0.05")
            reasons.append("exact_issue_date")
        elif days <= 3:
            score += Decimal("0.02")
            reasons.append("near_issue_date")
    return min(score, Decimal("1")), tuple(reasons)


def rank_invoice_candidates(
    *,
    observed_number: str | None,
    observed_amount_minor: int | None,
    candidates: list[tuple[UUID, str, int]],
) -> list[MatchCandidate]:
    ranked = []
    for invoice_id, number, amount_minor in candidates:
        score = Decimal("0")
        reasons = []
        if observed_number and observed_number.casefold() == number.casefold():
            score += Decimal("0.70")
            reasons.append("exact_invoice_number")
        if observed_amount_minor is not None and observed_amount_minor == amount_minor:
            score += Decimal("0.30")
            reasons.append("exact_amount")
        ranked.append(MatchCandidate(invoice_id, score, tuple(reasons)))
    return sorted(ranked, key=lambda item: (-item.score, str(item.invoice_id)))


def choose_unambiguous(candidates: list[MatchCandidate]) -> MatchCandidate | None:
    if not candidates or candidates[0].score < Decimal("0.70"):
        return None
    if len(candidates) > 1 and candidates[0].score == candidates[1].score:
        return None
    return candidates[0]
