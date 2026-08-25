from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.application.ai_agent import (
    AgentTaskResult,
    analyze_case,
    generate_follow_up_draft,
    validate_evidence_refs,
)
from backend.application.approvals import content_hash
from backend.application.permissions import Permission
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import tenant_session
from backend.infrastructure.llm_runtime import get_llm_provider
from backend.infrastructure.models import (
    Approval,
    Blocker,
    CaseDocument,
    CaseInvoice,
    Customer,
    EvidenceSpan,
    Invoice,
    LLMUsageEvent,
    PaymentCase,
)
from services.api.auth import Actor, current_actor, require_permission

router = APIRouter(prefix="/api/v1/ai", tags=["AI Agent"])


class AgentDraftRequest(BaseModel):
    to: list[str] = Field(min_length=1, max_length=5)
    cc: list[str] = Field(default_factory=list, max_length=5)
    objective: str = Field(min_length=3, max_length=500)


def _case_context(actor: Actor, case_id: UUID) -> tuple[dict[str, Any], set[str]]:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            select(PaymentCase, Invoice, Customer)
            .join(CaseInvoice, CaseInvoice.case_id == PaymentCase.id)
            .join(Invoice, Invoice.id == CaseInvoice.invoice_id)
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(PaymentCase.tenant_id == actor.tenant_id, PaymentCase.id == case_id)
            .order_by(Invoice.due_date)
        ).first()
        if row is None:
            raise HTTPException(404, "case not found")
        case, invoice, customer = row
        blockers = session.scalars(
            select(Blocker).where(
                Blocker.tenant_id == actor.tenant_id,
                Blocker.case_id == case_id,
                Blocker.active.is_(True),
            )
        ).all()
        evidence = session.scalars(
            select(EvidenceSpan)
            .join(CaseDocument, CaseDocument.document_id == EvidenceSpan.document_id)
            .where(CaseDocument.tenant_id == actor.tenant_id, CaseDocument.case_id == case_id)
            .limit(30)
        ).all()

    invoice_ref = f"invoice:{invoice.id}"
    evidence_rows = [
        {
            "id": f"evidence:{item.id}",
            "field": item.field_name,
            "quote": item.quote[:500],
            "location": (
                f"{item.sheet}!{item.cell_range}" if item.sheet else f"page:{item.page}"
            ),
        }
        for item in evidence
    ]
    blocker_rows = [
        {"id": f"blocker:{item.id}", "type": item.blocker_type} for item in blockers
    ]
    allowed_ids = {
        invoice_ref,
        *(item["id"] for item in evidence_rows),
        *(item["id"] for item in blocker_rows),
    }
    today = datetime.now(UTC).date()
    context = {
        "case": {"id": str(case.id), "status": case.status, "version": case.version},
        "customer": {"name": customer.name, "code": customer.code},
        "invoice": {
            "evidence_id": invoice_ref,
            "number": invoice.invoice_number,
            "outstanding_minor": invoice.outstanding_minor,
            "currency": invoice.currency,
            "due_date": invoice.due_date.isoformat(),
            "days_overdue": max(0, (today - invoice.due_date).days),
        },
        "active_blockers": blocker_rows,
        "evidence": evidence_rows,
    }
    return context, allowed_ids


def _record_usage(
    actor: Actor, task: str, task_result: AgentTaskResult, *, fallback: bool = False
) -> None:
    result = task_result.routed.result
    attempts = list(task_result.routed.attempts)
    settings = get_settings()
    with tenant_session(actor.tenant_id) as session:
        session.add(
            LLMUsageEvent(
                tenant_id=actor.tenant_id,
                occurred_at=datetime.now(UTC),
                task_type=task,
                provider=result.provider if result else settings.llm_default_provider,
                model=result.model if result else task_result.model,
                prompt_version=task_result.prompt_version,
                route=settings.llm_default_provider,
                fallback=fallback or len(attempts) > 1,
                success=result is not None and result.data is not None,
                schema_valid=result.schema_valid if result else False,
                latency_ms=result.latency_ms if result else 0,
                input_tokens=result.input_tokens if result else None,
                output_tokens=result.output_tokens if result else None,
                request_metadata={"attempts": attempts},
            )
        )


def _result_data(
    actor: Actor, task: str, result: AgentTaskResult, *, fallback: bool = False
) -> dict[str, Any]:
    _record_usage(actor, task, result, fallback=fallback)
    routed = result.routed.result
    if routed is None or routed.data is None:
        raise HTTPException(503, "AI provider is temporarily unavailable")
    return routed.data


@router.get("/status")
async def ai_status(actor: Annotated[Actor, Depends(current_actor)]) -> dict[str, object]:
    del actor
    settings = get_settings()
    configured = settings.llm_default_provider == "gemini" and bool(settings.gemini_api_key)
    return {
        "configured": configured,
        "provider": settings.llm_default_provider,
        "fast_model": settings.gemini_model_fast if configured else None,
        "reasoning_model": settings.gemini_model_reasoning if configured else None,
        "mode": "live" if configured else "offline",
        "guardrails": [
            "evidence_required",
            "prompt_injection_boundary",
            "human_approval_required",
            "external_send_disabled",
        ],
    }


@router.post("/cases/{case_id}/analyze")
async def analyze_case_endpoint(
    case_id: UUID,
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
) -> dict[str, object]:
    settings = get_settings()
    if settings.llm_default_provider != "gemini" or not settings.gemini_api_key:
        raise HTTPException(503, "Gemini is not configured")
    context, allowed_ids = _case_context(actor, case_id)
    result = await analyze_case(
        provider=get_llm_provider(), context=context, model=settings.gemini_model_reasoning
    )
    fallback_used = False
    if (
        result.routed.result is None
        and settings.gemini_model_fast != settings.gemini_model_reasoning
    ):
        _record_usage(actor, "case_analysis", result)
        result = await analyze_case(
            provider=get_llm_provider(), context=context, model=settings.gemini_model_fast
        )
        fallback_used = True
    data = _result_data(actor, "case_analysis", result, fallback=fallback_used)
    if not validate_evidence_refs(data, allowed_ids):
        raise HTTPException(422, "AI response referenced unsupported evidence")
    return {
        "case_id": str(case_id),
        "provider": settings.llm_default_provider,
        "model": result.model,
        "prompt_version": result.prompt_version,
        "analysis": data,
        "human_decision_required": True,
        "fallback_used": fallback_used,
    }


@router.post("/cases/{case_id}/draft")
async def draft_follow_up(
    case_id: UUID,
    request: AgentDraftRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.APPROVAL_SINGLE))],
) -> dict[str, object]:
    settings = get_settings()
    if settings.llm_default_provider != "gemini" or not settings.gemini_api_key:
        raise HTTPException(503, "Gemini is not configured")
    recipients = {item.strip().casefold() for item in (*request.to, *request.cc)}
    if not all("@" in item and "." in item.rsplit("@", 1)[-1] for item in recipients):
        raise HTTPException(422, "invalid email recipient")
    if settings.app_env == "portfolio" and not recipients <= settings.allowed_portfolio_emails:
        raise HTTPException(403, "portfolio drafts are restricted to the configured allowlist")
    context, allowed_ids = _case_context(actor, case_id)
    result = await generate_follow_up_draft(
        provider=get_llm_provider(),
        context=context,
        objective=request.objective,
        model=settings.gemini_model_fast,
    )
    data = _result_data(actor, "follow_up_draft", result)
    if not validate_evidence_refs(data, allowed_ids):
        raise HTTPException(422, "AI draft referenced unsupported evidence")
    subject = str(data.get("subject", "")).strip()
    body = str(data.get("body", "")).strip()
    if not subject or not body:
        raise HTTPException(422, "AI draft is incomplete")
    canonical = json.dumps(
        {
            "case_id": str(case_id),
            "to": request.to,
            "cc": request.cc,
            "subject": subject,
            "body": body,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    with tenant_session(actor.tenant_id) as session:
        approval = Approval(
            tenant_id=actor.tenant_id,
            case_id=case_id,
            content_hash=content_hash(canonical),
            status="PENDING",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        session.add(approval)
        session.flush()
        approval_id = approval.id
    return {
        "approval_id": str(approval_id),
        "content": canonical,
        "case_id": str(case_id),
        "to": request.to,
        "cc": request.cc,
        "subject": subject,
        "body": body,
        "evidence_refs": data["evidence_refs"],
        "safety_notes": data["safety_notes"],
        "provider": settings.llm_default_provider,
        "model": settings.gemini_model_fast,
        "status": "PENDING",
    }
