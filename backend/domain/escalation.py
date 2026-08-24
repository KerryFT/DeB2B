from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class EscalationStrategy(StrEnum):
    INTERNAL_FOLLOW_UP = "internal_follow_up"
    ACCOUNT_OWNER_INVOLVEMENT = "account_owner_involvement"
    AP_RESUBMISSION = "ap_resubmission"
    DOCUMENT_CORRECTION = "document_correction"
    MANAGER_REVIEW = "manager_review"
    CUSTOMER_MEETING = "customer_meeting"
    TEMPORARY_PAUSE = "temporary_pause"
    COMMERCIAL_REVIEW = "commercial_review"
    LEGAL_REVIEW_REFERRAL = "legal_review_referral"


@dataclass(frozen=True, slots=True)
class EscalationInput:
    as_of: date
    days_overdue: int
    amount_minor: int
    blocker: str | None
    disputed: bool
    missing_documents: bool
    response_count: int
    broken_promises: int
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Recommendation:
    rank: int
    strategy: EscalationStrategy
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    expected_outcome: str
    risk: str
    prerequisites: tuple[str, ...]
    next_review_date: date
    confidence: float
    rule_version: str = "escalation-rules-v1"


def recommend_escalation(item: EscalationInput) -> list[Recommendation]:
    if not item.evidence_ids:
        return [
            Recommendation(
                1,
                EscalationStrategy.MANAGER_REVIEW,
                ("insufficient_evidence",),
                (),
                "Collect verified case evidence",
                "MEDIUM",
                ("human_review",),
                item.as_of + timedelta(days=2),
                0.3,
            )
        ]
    strategies: list[tuple[EscalationStrategy, tuple[str, ...], str]] = []
    if item.missing_documents:
        strategies.append(
            (EscalationStrategy.AP_RESUBMISSION, ("missing_documents",), "Complete AP package")
        )
    if item.blocker in {"INCORRECT_DOCUMENT_DATA", "AMOUNT_MISMATCH"}:
        strategies.append(
            (EscalationStrategy.DOCUMENT_CORRECTION, ("document_error",), "Correct evidence")
        )
    if item.disputed:
        strategies.append(
            (EscalationStrategy.TEMPORARY_PAUSE, ("active_dispute",), "Avoid unsafe contact")
        )
        strategies.append(
            (EscalationStrategy.MANAGER_REVIEW, ("active_dispute",), "Review dispute response")
        )
    elif item.broken_promises:
        strategies.append(
            (
                EscalationStrategy.ACCOUNT_OWNER_INVOLVEMENT,
                ("broken_promise",),
                "Confirm revised payment plan",
            )
        )
    elif item.days_overdue > 30:
        strategies.append(
            (EscalationStrategy.CUSTOMER_MEETING, ("aging_over_30",), "Resolve blockers")
        )
    if not strategies:
        strategies.append(
            (EscalationStrategy.INTERNAL_FOLLOW_UP, ("low_risk_follow_up",), "Confirm next step")
        )
    return [
        Recommendation(
            rank,
            strategy,
            reasons,
            item.evidence_ids,
            outcome,
            "HIGH" if strategy == EscalationStrategy.LEGAL_REVIEW_REFERRAL else "LOW",
            ("human_acceptance",),
            item.as_of + timedelta(days=3),
            max(0.5, 0.9 - (rank - 1) * 0.1),
        )
        for rank, (strategy, reasons, outcome) in enumerate(strategies, start=1)
    ]
