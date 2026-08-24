from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OpenInvoice:
    id: UUID
    invoice_number: str
    outstanding_minor: int


@dataclass(frozen=True, slots=True)
class PaymentCandidate:
    invoice_ids: tuple[UUID, ...]
    allocations: tuple[int, ...]
    score: float
    reasons: tuple[str, ...]


def payment_candidates(
    *, amount_minor: int, reference: str, invoices: list[OpenInvoice]
) -> list[PaymentCandidate]:
    normalized = re.sub(r"[^A-Z0-9]", "", reference.upper())
    candidates = []
    for invoice in invoices:
        invoice_token = re.sub(r"[^A-Z0-9]", "", invoice.invoice_number.upper())
        referenced = invoice_token in normalized
        if amount_minor <= invoice.outstanding_minor and referenced:
            score = 1.0 if amount_minor == invoice.outstanding_minor else 0.85
            reason = "exact_reference_and_amount" if score == 1 else "referenced_partial_payment"
            candidates.append(PaymentCandidate((invoice.id,), (amount_minor,), score, (reason,)))
        elif amount_minor == invoice.outstanding_minor:
            candidates.append(
                PaymentCandidate((invoice.id,), (amount_minor,), 0.7, ("exact_amount",))
            )
    for size in (2, 3):
        for group in itertools.combinations(invoices, size):
            if sum(invoice.outstanding_minor for invoice in group) == amount_minor:
                referenced = all(
                    re.sub(r"[^A-Z0-9]", "", invoice.invoice_number.upper()) in normalized
                    for invoice in group
                )
                candidates.append(
                    PaymentCandidate(
                        tuple(invoice.id for invoice in group),
                        tuple(invoice.outstanding_minor for invoice in group),
                        0.95 if referenced else 0.65,
                        ("combined_exact_sum", "all_references" if referenced else "amount_only"),
                    )
                )
    return sorted(candidates, key=lambda candidate: (-candidate.score, candidate.invoice_ids))


def choose_payment_candidate(candidates: list[PaymentCandidate]) -> PaymentCandidate | None:
    if not candidates or candidates[0].score < 0.85:
        return None
    if len(candidates) > 1 and candidates[0].score == candidates[1].score:
        return None
    return candidates[0]
