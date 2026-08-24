from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class RootCause(StrEnum):
    PRICING_AMOUNT_MISMATCH = "pricing_amount_mismatch"
    PO_MISMATCH = "po_mismatch"
    MISSING_INVALID_DOCUMENT = "missing_invalid_document"
    DELIVERY_QUALITY_ISSUE = "delivery_quality_issue"
    ACCEPTANCE_SIGNATURE = "acceptance_signature"
    TAX_INVOICE_COMPLIANCE = "tax_invoice_compliance"
    DUPLICATE_INVOICE = "duplicate_invoice"
    CONTRACTUAL_TERM_AMBIGUITY = "contractual_term_ambiguity"
    CUSTOMER_INTERNAL_APPROVAL = "customer_internal_approval"
    PAYMENT_ALREADY_MADE_UNMATCHED = "payment_already_made_unmatched"
    SELLER_OPERATIONAL_ERROR = "seller_operational_error"
    CUSTOMER_CASH_FLOW = "customer_cash_flow"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RootCauseAssessment:
    primary: RootCause
    contributing: tuple[RootCause, ...]
    confidence: float
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    taxonomy_version: str
    first_detected_at: datetime
    status: str = "OPEN"
    resolution: str | None = None
    resolved_at: datetime | None = None
    reopen_count: int = 0
    human_corrected: bool = False


KEYWORD_RULES: tuple[tuple[RootCause, tuple[str, ...]], ...] = (
    (RootCause.PRICING_AMOUNT_MISMATCH, ("amount_mismatch", "price_mismatch")),
    (RootCause.PO_MISMATCH, ("po_mismatch",)),
    (RootCause.MISSING_INVALID_DOCUMENT, ("missing_document", "invalid_document")),
    (RootCause.DELIVERY_QUALITY_ISSUE, ("delivery_issue", "quality_issue")),
    (RootCause.ACCEPTANCE_SIGNATURE, ("missing_signature", "acceptance")),
    (RootCause.TAX_INVOICE_COMPLIANCE, ("tax_error", "invoice_compliance")),
    (RootCause.DUPLICATE_INVOICE, ("duplicate_invoice",)),
    (RootCause.CONTRACTUAL_TERM_AMBIGUITY, ("term_ambiguity",)),
    (RootCause.CUSTOMER_INTERNAL_APPROVAL, ("internal_approval",)),
    (RootCause.PAYMENT_ALREADY_MADE_UNMATCHED, ("payment_unmatched",)),
    (RootCause.SELLER_OPERATIONAL_ERROR, ("seller_error",)),
    (RootCause.CUSTOMER_CASH_FLOW, ("cash_flow",)),
)


def assess_root_cause(
    *, reason_codes: list[str], evidence_ids: list[str], detected_at: datetime
) -> RootCauseAssessment:
    if not evidence_ids:
        return RootCauseAssessment(
            RootCause.UNKNOWN,
            (),
            0.0,
            (),
            tuple(reason_codes),
            "root-cause-v1",
            detected_at,
        )
    matched = [cause for cause, keys in KEYWORD_RULES if set(keys) & set(reason_codes)]
    primary = matched[0] if matched else RootCause.UNKNOWN
    confidence = min(0.95, 0.55 + 0.1 * len(set(reason_codes))) if matched else 0.25
    return RootCauseAssessment(
        primary,
        tuple(dict.fromkeys(matched[1:])),
        confidence,
        tuple(dict.fromkeys(evidence_ids)),
        tuple(dict.fromkeys(reason_codes)),
        "root-cause-v1",
        detected_at,
    )


def correct_assessment(
    assessment: RootCauseAssessment,
    *,
    primary: RootCause,
    contributing: tuple[RootCause, ...],
) -> RootCauseAssessment:
    if primary in contributing:
        raise ValueError("primary cause cannot also be contributing")
    return replace(
        assessment,
        primary=primary,
        contributing=contributing,
        confidence=1.0,
        human_corrected=True,
    )


def resolve_assessment(
    assessment: RootCauseAssessment, *, resolution: str, resolved_at: datetime
) -> RootCauseAssessment:
    if not resolution.strip() or resolved_at < assessment.first_detected_at:
        raise ValueError("valid resolution and timestamp are required")
    return replace(
        assessment, status="RESOLVED", resolution=resolution.strip(), resolved_at=resolved_at
    )


def reopen_assessment(assessment: RootCauseAssessment) -> RootCauseAssessment:
    if assessment.status != "RESOLVED":
        raise ValueError("only a resolved dispute can be reopened")
    return replace(
        assessment,
        status="OPEN",
        resolution=None,
        resolved_at=None,
        reopen_count=assessment.reopen_count + 1,
    )
