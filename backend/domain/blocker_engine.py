from __future__ import annotations

from dataclasses import dataclass

from backend.domain.blockers import BlockerType


@dataclass(frozen=True, slots=True)
class BlockerDecision:
    blockers: tuple[BlockerType, ...]
    next_task: str
    reasons: tuple[str, ...]


def classify_missing_documents(*, has_invoice: bool, has_acceptance: bool) -> BlockerDecision:
    blockers = []
    reasons = []
    if not has_invoice:
        blockers.append(BlockerType.MISSING_PAYMENT_DOCUMENT)
        reasons.append("invoice evidence is absent")
    if not has_acceptance:
        blockers.append(BlockerType.MISSING_ACCEPTANCE_OR_DELIVERY_CONFIRMATION)
        reasons.append("acceptance or delivery evidence is absent")
    next_task = "REQUEST_MISSING_DOCUMENTS" if blockers else "REVIEW_MATCH"
    return BlockerDecision(tuple(blockers), next_task, tuple(reasons))


def classify_case(
    *,
    has_invoice: bool,
    has_acceptance: bool,
    document_data_matches: bool,
    customer_disputed: bool,
    promise_due: bool,
    promise_paid: bool,
) -> BlockerDecision:
    base = classify_missing_documents(has_invoice=has_invoice, has_acceptance=has_acceptance)
    blockers = list(base.blockers)
    reasons = list(base.reasons)
    if has_invoice and not document_data_matches:
        blockers.append(BlockerType.INCORRECT_DOCUMENT_DATA)
        reasons.append("critical document fields conflict")
    if customer_disputed:
        blockers.append(BlockerType.CUSTOMER_DISPUTE)
        reasons.append("customer explicitly disputes the debt")
    if promise_due and not promise_paid:
        blockers.append(BlockerType.BROKEN_PROMISE_TO_PAY)
        reasons.append("promise date elapsed without matched payment")
    if len(blockers) > 3:
        next_task = "MANUAL_REVIEW"
    elif blockers:
        next_task = "RESOLVE_BLOCKERS"
    else:
        next_task = "REVIEW_MATCH"
    return BlockerDecision(tuple(blockers), next_task, tuple(reasons))
