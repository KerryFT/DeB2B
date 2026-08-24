from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from backend.application.mutation import MutationContext, record_mutation
from backend.application.permissions import Permission
from backend.domain.account_manager_benchmark import ManagerCaseOutcome, benchmark_managers
from backend.domain.cashflow_forecast_v2 import (
    CashFlowInput,
    aggregate_by_currency,
    probabilistic_cashflow,
)
from backend.domain.customer_behavior import PaymentHistory, build_behavior_profile
from backend.domain.dispute_root_causes import RootCause
from backend.domain.email_automation import (
    AutomationCandidate,
    AutomationMode,
    AutomationPolicy,
    evaluate_automation,
)
from backend.domain.escalation import EscalationInput, recommend_escalation
from backend.domain.probability_to_pay import predict_probability
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import tenant_session
from backend.infrastructure.models import (
    AutomationDecisionRecord,
    AutomationPolicyRecord,
    Blocker,
    CaseInvoice,
    Customer,
    DisputeRootCauseRecord,
    EscalationRecommendationRecord,
    Invoice,
    PaymentCase,
)
from services.api.auth import Actor, current_actor, require_permission

router = APIRouter(prefix="/api/v2")


def _as_of_hash(*values: object) -> str:
    return sha256("|".join(str(value) for value in values).encode()).hexdigest()


@router.get("/governance")
async def governance_status(
    actor: Annotated[Actor, Depends(current_actor)],
) -> dict[str, object]:
    return {
        "tenant_id": str(actor.tenant_id),
        "feature_version": "ar-point-in-time-v1",
        "probability_model": "segment-beta-baseline-v1",
        "forecast_model": "probability-components-v1",
        "dataset_version": "synthetic-v3",
        "horizons_days": [7, 14, 30],
        "point_in_time_policy": "occurred_at <= as_of",
        "stale_behavior": "fallback_to_segment_baseline",
    }


@router.get("/probability-to-pay")
async def probability_to_pay(
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
    as_of: date | None = None,
) -> dict[str, object]:
    effective_as_of = as_of or datetime.now(UTC).date()
    if effective_as_of != datetime.now(UTC).date():
        raise HTTPException(
            422,
            "historical as_of requires a persisted point-in-time feature snapshot/backtest run",
        )
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            select(PaymentCase, Invoice, Customer)
            .join(CaseInvoice, CaseInvoice.case_id == PaymentCase.id)
            .join(Invoice, Invoice.id == CaseInvoice.invoice_id)
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(
                PaymentCase.tenant_id == actor.tenant_id,
                Invoice.issue_date <= effective_as_of,
                Invoice.outstanding_minor > 0,
            )
            .order_by(Invoice.due_date)
        ).all()
    predictions = []
    rates = {
        7: {"current": 0.62, "overdue": 0.28},
        14: {"current": 0.76, "overdue": 0.43},
        30: {"current": 0.9, "overdue": 0.67},
    }
    for case, invoice, customer in rows:
        segment = "overdue" if invoice.due_date < effective_as_of else "current"
        snapshot_hash = _as_of_hash(invoice.id, invoice.outstanding_minor, effective_as_of)
        prediction = predict_probability(
            entity_id=str(invoice.id),
            segment=segment,
            as_of=effective_as_of,
            rates_by_horizon=rates,
            feature_snapshot_hash=snapshot_hash,
            disputed=case.status == "DISPUTED",
            sparse=True,
        )
        predictions.append(
            {
                **asdict(prediction),
                "case_id": str(case.id),
                "invoice_number": invoice.invoice_number,
                "customer": customer.name,
                "outstanding_minor": invoice.outstanding_minor,
                "currency": invoice.currency,
            }
        )
    return {
        "as_of": effective_as_of,
        "model_version": "segment-beta-baseline-v1",
        "feature_version": "ar-point-in-time-v1",
        "predictions": predictions,
        "disclaimer": "Operational estimate; not accounting truth or an action decision.",
    }


@router.get("/cash-flow")
async def cash_flow(
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
    horizon_days: int = 30,
    downside_factor: float = 0.8,
    upside_factor: float = 1.1,
) -> dict[str, object]:
    if horizon_days not in {7, 14, 30}:
        raise HTTPException(422, "horizon_days must be 7, 14 or 30")
    if not 0 <= downside_factor <= 1 or not 1 <= upside_factor <= 1.5:
        raise HTTPException(422, "scenario factors outside safe bounds")
    today = datetime.now(UTC).date()
    rates = {7: 0.35, 14: 0.52, 30: 0.72}
    with tenant_session(actor.tenant_id) as session:
        invoices = session.scalars(
            select(Invoice).where(
                Invoice.tenant_id == actor.tenant_id,
                Invoice.issue_date <= today,
                Invoice.outstanding_minor > 0,
            )
        ).all()
    inputs = [
        CashFlowInput(
            str(item.id),
            str(item.customer_id),
            item.account_owner or "unassigned",
            item.currency,
            item.outstanding_minor,
            item.due_date,
            {horizon_days: rates[horizon_days]},
        )
        for item in invoices
    ]
    components = probabilistic_cashflow(
        inputs,
        horizon_days=horizon_days,
        downside_factor=downside_factor,
        upside_factor=upside_factor,
    )
    contractual = sum(item.outstanding_minor for item in invoices)
    reconciled = sum(item.contractual_minor for item in components)
    return {
        "as_of": today,
        "cutoff": today,
        "horizon_days": horizon_days,
        "model_version": "probability-components-v1",
        "scenario_version": "bounded-factors-v1",
        "by_currency": aggregate_by_currency(components),
        "components": [asdict(item) for item in components],
        "reconciliation": {
            "source_outstanding_minor": contractual,
            "component_contractual_minor": reconciled,
            "difference_minor": contractual - reconciled,
        },
        "disclaimer": "Forecast only; not an accounting cash position.",
    }


@router.get("/customer-behavior")
async def customer_behavior(
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
    window_days: int = 365,
) -> dict[str, object]:
    if not 30 <= window_days <= 3650:
        raise HTTPException(422, "window_days must be between 30 and 3650")
    today = datetime.now(UTC).date()
    with tenant_session(actor.tenant_id) as session:
        customers = session.scalars(
            select(Customer).where(Customer.tenant_id == actor.tenant_id).order_by(Customer.name)
        ).all()
        profiles: list[dict[str, object]] = []
        for customer in customers:
            invoices = session.scalars(
                select(Invoice).where(
                    Invoice.tenant_id == actor.tenant_id,
                    Invoice.customer_id == customer.id,
                    Invoice.issue_date <= today,
                )
            ).all()
            history = [
                PaymentHistory(
                    str(item.id),
                    item.amount_minor,
                    item.due_date,
                    today if item.outstanding_minor == 0 else None,
                    occurred_at=item.issue_date,
                )
                for item in invoices
            ]
            profile = build_behavior_profile(history, as_of=today, window_days=window_days)
            profiles.append(
                {"customer_id": str(customer.id), "customer": customer.name, **asdict(profile)}
            )
    return {
        "as_of": today,
        "profile_version": "behavior-profile-v1",
        "profiles": profiles,
        "label_policy": "descriptive_only_no_credit_or_moral_judgment",
    }


class DisputeCreate(BaseModel):
    case_id: UUID
    primary_cause: RootCause
    contributing_causes: list[RootCause] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)
    reason_codes: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


@router.get("/disputes")
async def disputes(
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = session.scalars(
            select(DisputeRootCauseRecord).where(
                DisputeRootCauseRecord.tenant_id == actor.tenant_id
            )
        ).all()
        aggregates = session.execute(
            select(
                DisputeRootCauseRecord.primary_cause,
                func.count(func.distinct(DisputeRootCauseRecord.id)),
                func.coalesce(func.sum(Invoice.outstanding_minor), 0),
            )
            .join(PaymentCase, PaymentCase.id == DisputeRootCauseRecord.case_id)
            .join(CaseInvoice, CaseInvoice.case_id == PaymentCase.id)
            .join(Invoice, Invoice.id == CaseInvoice.invoice_id)
            .where(DisputeRootCauseRecord.tenant_id == actor.tenant_id)
            .group_by(DisputeRootCauseRecord.primary_cause)
        ).all()
        resolved_count = sum(item.status == "RESOLVED" for item in rows)
        unknown_count = sum(item.primary_cause == RootCause.UNKNOWN.value for item in rows)
        reopened_count = sum(item.reopen_count > 0 for item in rows)
        resolution_hours = [
            (item.resolved_at - item.first_detected_at).total_seconds() / 3600
            for item in rows
            if item.resolved_at is not None
        ]
    return {
        "taxonomy_version": "root-cause-v1",
        "aggregate": [
            {"cause": cause, "count": count, "value_at_risk_minor": int(value)}
            for cause, count, value in aggregates
        ],
        "metrics": {
            "resolved_count": resolved_count,
            "unknown_rate": unknown_count / len(rows) if rows else 0,
            "reopen_rate": reopened_count / len(rows) if rows else 0,
            "average_resolution_hours": (
                sum(resolution_hours) / len(resolution_hours) if resolution_hours else None
            ),
        },
        "items": [
            {
                "id": str(item.id),
                "case_id": str(item.case_id),
                "primary_cause": item.primary_cause,
                "contributing_causes": item.contributing_causes,
                "confidence": item.confidence,
                "evidence_ids": item.evidence_ids,
                "status": item.status,
                "reopen_count": item.reopen_count,
            }
            for item in rows
        ],
        "inference_notice": "Categories are evidence-backed inferences, not proven causation.",
    }


@router.post("/disputes")
async def record_dispute(
    request: DisputeCreate,
    actor: Annotated[Actor, Depends(require_permission(Permission.DISPUTE_CORRECT))],
) -> dict[str, str]:
    if request.primary_cause in request.contributing_causes:
        raise HTTPException(422, "primary cause cannot also be contributing")
    with tenant_session(actor.tenant_id) as session:
        case = session.scalar(
            select(PaymentCase).where(
                PaymentCase.tenant_id == actor.tenant_id, PaymentCase.id == request.case_id
            )
        )
        if case is None:
            raise HTTPException(404, "case not found")
        item = DisputeRootCauseRecord(
            tenant_id=actor.tenant_id,
            case_id=request.case_id,
            primary_cause=request.primary_cause.value,
            contributing_causes=[cause.value for cause in request.contributing_causes],
            confidence=str(request.confidence),
            evidence_ids=request.evidence_ids,
            reason_codes=request.reason_codes,
            taxonomy_version="root-cause-v1",
            first_detected_at=datetime.now(UTC),
            status="OPEN",
            reopen_count=0,
            corrected_by=actor.user_id,
        )
        session.add(item)
        session.flush()
        record_mutation(
            session,
            context=MutationContext(actor.tenant_id, "USER", str(actor.user_id), str(uuid4())),
            action="DISPUTE_ROOT_CAUSE_CORRECTED",
            aggregate_type="DISPUTE",
            aggregate_id=item.id,
            audit_payload=request.model_dump(mode="json"),
            event_topic="dispute.root_cause.corrected.v1",
            event_payload={"case_id": str(request.case_id), "root_cause_id": str(item.id)},
        )
        return {"id": str(item.id), "status": item.status}


@router.post("/escalation/{case_id}/generate")
async def escalation(
    case_id: UUID,
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
) -> dict[str, object]:
    today = datetime.now(UTC).date()
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            select(PaymentCase, Invoice)
            .join(CaseInvoice, CaseInvoice.case_id == PaymentCase.id)
            .join(Invoice, Invoice.id == CaseInvoice.invoice_id)
            .where(PaymentCase.tenant_id == actor.tenant_id, PaymentCase.id == case_id)
        ).first()
        if row is None:
            raise HTTPException(404, "case not found")
        case, invoice = row
        blockers = session.scalars(
            select(Blocker).where(
                Blocker.tenant_id == actor.tenant_id,
                Blocker.case_id == case_id,
                Blocker.active.is_(True),
            )
        ).all()
    evidence = tuple(f"blocker:{item.id}" for item in blockers) or (f"invoice:{invoice.id}",)
    recommendations = recommend_escalation(
        EscalationInput(
            today,
            max(0, (today - invoice.due_date).days),
            invoice.outstanding_minor,
            blockers[0].blocker_type if blockers else None,
            case.status == "DISPUTED",
            any(item.blocker_type == "MISSING_DOCUMENT" for item in blockers),
            0,
            0,
            evidence,
        )
    )
    with tenant_session(actor.tenant_id) as session:
        stored: list[EscalationRecommendationRecord] = []
        for item in recommendations:
            record = EscalationRecommendationRecord(
                tenant_id=actor.tenant_id,
                case_id=case_id,
                generated_at=datetime.now(UTC),
                rank=item.rank,
                strategy=item.strategy.value,
                rationale={
                    "reason_codes": item.reason_codes,
                    "expected_outcome": item.expected_outcome,
                    "risk": item.risk,
                    "prerequisites": item.prerequisites,
                    "next_review_date": item.next_review_date.isoformat(),
                },
                evidence_ids=list(item.evidence_ids),
                confidence=str(item.confidence),
                rule_version=item.rule_version,
            )
            session.add(record)
            stored.append(record)
        session.flush()
        ids = [str(item.id) for item in stored]
    return {
        "case_id": str(case_id),
        "as_of": today,
        "human_decision_required": True,
        "recommendations": [
            {"id": item_id, **asdict(item)}
            for item_id, item in zip(ids, recommendations, strict=True)
        ],
    }


LiteralFeedback = Literal["accepted", "edited", "rejected", "ignored"]


class EscalationFeedback(BaseModel):
    decision: LiteralFeedback


@router.post("/escalation/recommendations/{recommendation_id}/feedback")
async def escalation_feedback(
    recommendation_id: UUID,
    request: EscalationFeedback,
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_EDIT))],
) -> dict[str, str]:
    with tenant_session(actor.tenant_id) as session:
        record = session.scalar(
            select(EscalationRecommendationRecord).where(
                EscalationRecommendationRecord.tenant_id == actor.tenant_id,
                EscalationRecommendationRecord.id == recommendation_id,
            )
        )
        if record is None:
            raise HTTPException(404, "recommendation not found")
        record.feedback = request.decision
        record.feedback_by = actor.user_id
        return {"id": str(record.id), "feedback": record.feedback}


@router.get("/account-manager-benchmark")
async def account_manager_benchmark(
    actor: Annotated[Actor, Depends(require_permission(Permission.BENCHMARK_VIEW))],
) -> dict[str, object]:
    today = datetime.now(UTC).date()
    with tenant_session(actor.tenant_id) as session:
        invoices = session.scalars(
            select(Invoice).where(Invoice.tenant_id == actor.tenant_id)
        ).all()
    outcomes = [
        ManagerCaseOutcome(
            str(item.id),
            item.account_owner or "unassigned",
            max(1.0, (today - item.due_date).days * 4.0),
            2.0,
            None,
            8.0,
            1 - item.outstanding_minor / item.amount_minor if item.amount_minor else 0,
            1 + min(2, max(0, (today - item.due_date).days)) / 90,
        )
        for item in invoices
    ]
    rows = benchmark_managers(outcomes, minimum_sample=3)
    return {
        "as_of": today,
        "metric_version": "portfolio-adjusted-v1",
        "purpose": "operational coaching only; no automated HR decision",
        "minimum_sample": 3,
        "benchmarks": [asdict(item) for item in rows],
    }


class AutomationPolicyRequest(BaseModel):
    mode: AutomationMode = AutomationMode.DISABLED
    kill_switch: bool = True
    canary_percent: int = Field(default=0, ge=0, le=10)
    daily_send_cap: int = Field(default=10, ge=1, le=100)
    confirmation: str = ""


@router.get("/automation/policy")
async def automation_policy(
    actor: Annotated[Actor, Depends(require_permission(Permission.AUTOMATION_AUDIT))],
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        policy = session.scalar(
            select(AutomationPolicyRecord)
            .where(AutomationPolicyRecord.tenant_id == actor.tenant_id)
            .order_by(AutomationPolicyRecord.enabled_at.desc().nullslast())
        )
    settings = get_settings()
    if policy is None:
        return {
            "mode": "disabled",
            "kill_switch": True,
            "policy_version": "auto-email-v1",
            "external_delivery_enabled": settings.automation_external_delivery_enabled,
            "global_kill_switch": settings.automation_global_kill_switch,
        }
    return {
        "id": str(policy.id),
        "mode": policy.mode,
        "kill_switch": policy.kill_switch,
        "policy_version": policy.policy_version,
        "config": policy.config,
        "external_delivery_enabled": settings.automation_external_delivery_enabled,
        "global_kill_switch": settings.automation_global_kill_switch,
    }


@router.post("/automation/policy")
async def set_automation_policy(
    request: AutomationPolicyRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.AUTOMATION_MANAGE))],
) -> dict[str, object]:
    if request.mode in {AutomationMode.CANARY, AutomationMode.ENABLED}:
        if request.confirmation != "ENABLE LOW RISK EMAIL AUTOMATION":
            raise HTTPException(409, "explicit enable confirmation is required")
        if request.kill_switch:
            raise HTTPException(409, "disable the tenant kill switch explicitly to enable")
    policy_version = f"auto-email-v1-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    with tenant_session(actor.tenant_id) as session:
        item = AutomationPolicyRecord(
            tenant_id=actor.tenant_id,
            mode=request.mode.value,
            policy_version=policy_version,
            config={
                "canary_percent": request.canary_percent,
                "daily_send_cap": request.daily_send_cap,
                "low_risk_only": True,
            },
            kill_switch=request.kill_switch,
            enabled_by=actor.user_id,
            enabled_at=datetime.now(UTC),
        )
        session.add(item)
        session.flush()
        record_mutation(
            session,
            context=MutationContext(actor.tenant_id, "USER", str(actor.user_id), str(uuid4())),
            action="AUTOMATION_POLICY_CHANGED",
            aggregate_type="AUTOMATION_POLICY",
            aggregate_id=item.id,
            audit_payload={"mode": request.mode, "kill_switch": request.kill_switch},
            event_topic="automation.policy.changed.v1",
            event_payload={"policy_id": str(item.id), "mode": request.mode},
        )
        return {"id": str(item.id), "mode": item.mode, "kill_switch": item.kill_switch}


@router.post("/automation/evaluate/{case_id}")
async def evaluate_case_automation(
    case_id: UUID,
    actor: Annotated[Actor, Depends(require_permission(Permission.AUTOMATION_AUDIT))],
) -> dict[str, object]:
    settings = get_settings()
    now = datetime.now(UTC)
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            select(PaymentCase, Invoice)
            .join(CaseInvoice, CaseInvoice.case_id == PaymentCase.id)
            .join(Invoice, Invoice.id == CaseInvoice.invoice_id)
            .where(PaymentCase.tenant_id == actor.tenant_id, PaymentCase.id == case_id)
        ).first()
        if row is None:
            raise HTTPException(404, "case not found")
        case, invoice = row
        record = session.scalar(
            select(AutomationPolicyRecord)
            .where(AutomationPolicyRecord.tenant_id == actor.tenant_id)
            .order_by(AutomationPolicyRecord.enabled_at.desc().nullslast())
        )
        mode = AutomationMode(record.mode) if record else AutomationMode.DISABLED
        policy = AutomationPolicy(
            mode=mode,
            policy_version=record.policy_version if record else "auto-email-v1",
            canary_percent=int(record.config.get("canary_percent", 0)) if record else 0,
            daily_send_cap=int(record.config.get("daily_send_cap", 10)) if record else 10,
            tenant_kill_switch=record.kill_switch if record else True,
        )
        candidate = AutomationCandidate(
            str(actor.tenant_id),
            str(case.id),
            case.version,
            invoice.outstanding_minor,
            max(0, (now.date() - invoice.due_date).days),
            invoice.outstanding_minor <= 0,
            case.status == "DISPUTED",
            False,
            False,
            False,
            "unconfigured-recipient",
            False,
            False,
            False,
            True,
            True,
            False,
            True,
            0,
            0.0,
            True,
            0,
            None,
            now,
        )
        decision = evaluate_automation(
            candidate,
            policy,
            global_kill_switch=settings.automation_global_kill_switch,
        )
        if record is not None:
            existing = session.scalar(
                select(AutomationDecisionRecord).where(
                    AutomationDecisionRecord.tenant_id == actor.tenant_id,
                    AutomationDecisionRecord.idempotency_key == decision.idempotency_key,
                )
            )
            if existing is None:
                decision_record = AutomationDecisionRecord(
                    tenant_id=actor.tenant_id,
                    case_id=case.id,
                    policy_id=record.id,
                    evaluated_at=now,
                    case_version=case.version,
                    disposition=decision.disposition,
                    eligible=decision.eligible,
                    exclusions=list(decision.exclusions),
                    idempotency_key=decision.idempotency_key,
                    delivery_status="NOT_SENT",
                )
                session.add(decision_record)
                session.flush()
                record_mutation(
                    session,
                    context=MutationContext(actor.tenant_id, "SYSTEM", None, str(uuid4())),
                    action="AUTOMATION_DECISION_RECORDED",
                    aggregate_type="AUTOMATION_DECISION",
                    aggregate_id=decision_record.id,
                    audit_payload={
                        "disposition": decision.disposition,
                        "exclusions": decision.exclusions,
                        "delivery_status": "NOT_SENT",
                    },
                    event_topic="automation.decision.recorded.v1",
                    event_payload={"decision_id": str(decision_record.id)},
                )
    return {
        **asdict(decision),
        "external_delivery_attempted": False,
        "external_delivery_enabled": settings.automation_external_delivery_enabled,
    }
