from __future__ import annotations

from enum import StrEnum


class CaseStatus(StrEnum):
    IMPORTED = "IMPORTED"
    COLLECTING_DOCUMENTS = "COLLECTING_DOCUMENTS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    READY_TO_SUBMIT = "READY_TO_SUBMIT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    DRAFT_CREATED = "DRAFT_CREATED"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    DISPUTED = "DISPUTED"
    PROMISE_TO_PAY = "PROMISE_TO_PAY"
    OVERDUE = "OVERDUE"
    RECONCILIATION_REVIEW = "RECONCILIATION_REVIEW"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PAID = "PAID"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


TERMINAL = {CaseStatus.PAID, CaseStatus.CLOSED, CaseStatus.CANCELLED}

ALLOWED: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.IMPORTED: {CaseStatus.COLLECTING_DOCUMENTS, CaseStatus.READY_FOR_REVIEW},
    CaseStatus.COLLECTING_DOCUMENTS: {CaseStatus.READY_FOR_REVIEW, CaseStatus.MANUAL_REVIEW},
    CaseStatus.READY_FOR_REVIEW: {CaseStatus.READY_TO_SUBMIT, CaseStatus.MANUAL_REVIEW},
    CaseStatus.READY_TO_SUBMIT: {CaseStatus.AWAITING_APPROVAL, CaseStatus.MANUAL_REVIEW},
    CaseStatus.AWAITING_APPROVAL: {CaseStatus.DRAFT_CREATED, CaseStatus.READY_TO_SUBMIT},
    CaseStatus.DRAFT_CREATED: {CaseStatus.AWAITING_RESPONSE},
    CaseStatus.AWAITING_RESPONSE: {
        CaseStatus.DISPUTED,
        CaseStatus.PROMISE_TO_PAY,
        CaseStatus.OVERDUE,
        CaseStatus.RECONCILIATION_REVIEW,
    },
    CaseStatus.DISPUTED: {CaseStatus.READY_FOR_REVIEW, CaseStatus.MANUAL_REVIEW, CaseStatus.CLOSED},
    CaseStatus.PROMISE_TO_PAY: {CaseStatus.RECONCILIATION_REVIEW, CaseStatus.OVERDUE},
    CaseStatus.OVERDUE: {CaseStatus.AWAITING_APPROVAL, CaseStatus.RECONCILIATION_REVIEW},
    CaseStatus.RECONCILIATION_REVIEW: {CaseStatus.PAID, CaseStatus.MANUAL_REVIEW},
    CaseStatus.MANUAL_REVIEW: {
        CaseStatus.COLLECTING_DOCUMENTS,
        CaseStatus.READY_FOR_REVIEW,
        CaseStatus.RECONCILIATION_REVIEW,
        CaseStatus.CANCELLED,
    },
}


class IllegalTransition(ValueError):
    pass


def ensure_transition(current: CaseStatus, target: CaseStatus) -> None:
    if current in TERMINAL or target not in ALLOWED.get(current, set()):
        raise IllegalTransition(f"illegal case transition: {current} -> {target}")
