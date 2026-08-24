from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.application.approvals import approve_content
from backend.application.bulk_approvals import BulkItem, preview_bulk
from backend.application.llm_analytics import LLMEvent, PricingVersion, aggregate_online
from backend.application.permissions import Permission, permissions_for_role
from backend.application.v1_connectors import (
    ZaloRecipient,
    ZaloTemplate,
    preview_zalo_notification,
)
from backend.domain.aging_forecast import ForecastInvoice, baseline_forecast, cashflow_buckets
from backend.domain.payment_rules import RuleDefinition, detect_conflicts, evaluate_rules
from backend.infrastructure.database import tenant_session
from backend.infrastructure.models import (
    Approval,
    BulkApprovalBatch,
    BulkApprovalItem,
    ConnectorConfig,
    Customer,
    Invoice,
    LLMPricing,
    LLMQualityMetric,
    LLMUsageEvent,
    PaymentCase,
    PaymentRule,
)
from services.api.auth import Actor, current_actor, require_permission

router = APIRouter(prefix="/api/v1")


@router.get("/permissions")
async def my_permissions(actor: Annotated[Actor, Depends(current_actor)]) -> dict[str, object]:
    return {
        "role": actor.role,
        "permissions": sorted(item.value for item in permissions_for_role(actor.role)),
    }


class RuleSimulationRequest(BaseModel):
    as_of: date
    rules: list[RuleDefinition]


@router.post("/payment-rules/simulate")
async def simulate_payment_rules(
    request: RuleSimulationRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.RULE_CREATE))],
) -> dict[str, object]:
    del actor
    conflicts = detect_conflicts(request.rules)
    if conflicts:
        raise HTTPException(409, {"conflicts": conflicts})
    return evaluate_rules(request.rules, as_of=request.as_of).model_dump(mode="json")


class RuleCreateRequest(BaseModel):
    customer_id: UUID | None = None
    rule: RuleDefinition


@router.post("/payment-rules")
async def create_payment_rule(
    request: RuleCreateRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.RULE_CREATE))],
) -> dict[str, str]:
    with tenant_session(actor.tenant_id) as session:
        if request.customer_id is not None:
            customer = session.scalar(
                select(Customer).where(
                    Customer.tenant_id == actor.tenant_id, Customer.id == request.customer_id
                )
            )
            if customer is None:
                raise HTTPException(404, "customer not found")
        record = PaymentRule(
            tenant_id=actor.tenant_id,
            customer_id=request.customer_id,
            rule_type=request.rule.rule_type.value,
            scope=request.rule.scope.value,
            priority=request.rule.priority,
            effective_from=request.rule.effective_from,
            expires_on=request.rule.expires_on,
            version=request.rule.version,
            status="DRAFT",
            definition=request.rule.model_dump(mode="json"),
            created_by=actor.user_id,
        )
        session.add(record)
        session.flush()
        return {"id": str(record.id), "status": record.status}


@router.post("/payment-rules/{rule_id}/publish")
async def publish_payment_rule(
    rule_id: UUID,
    actor: Annotated[Actor, Depends(require_permission(Permission.RULE_PUBLISH))],
) -> dict[str, str]:
    with tenant_session(actor.tenant_id) as session:
        record = session.scalar(
            select(PaymentRule)
            .where(PaymentRule.tenant_id == actor.tenant_id, PaymentRule.id == rule_id)
            .with_for_update()
        )
        if record is None:
            raise HTTPException(404, "rule not found")
        if record.created_by == actor.user_id:
            raise HTTPException(409, "maker-checker requires a different publisher")
        if record.status != "DRAFT":
            raise HTTPException(409, "only draft rules can be published")
        RuleDefinition.model_validate(record.definition)
        record.status = "PUBLISHED"
        record.published_by = actor.user_id
        return {"id": str(record.id), "status": record.status}


@router.get("/connectors")
async def connector_status(
    actor: Annotated[Actor, Depends(require_permission(Permission.CONNECTOR_MANAGE))],
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = session.scalars(
            select(ConnectorConfig)
            .where(ConnectorConfig.tenant_id == actor.tenant_id)
            .order_by(ConnectorConfig.provider)
        ).all()
        return [
            {
                "provider": item.provider,
                "environment": item.environment,
                "capabilities": item.capabilities,
                "enabled": item.enabled,
                "secret_configured": bool(item.secret_reference),
            }
            for item in rows
        ]


@router.post("/connectors/{provider}/retry")
async def retry_connector(
    provider: str,
    actor: Annotated[Actor, Depends(require_permission(Permission.EXTERNAL_ACTION_RETRY))],
) -> dict[str, str]:
    if provider not in {"misa", "outlook", "zalo"}:
        raise HTTPException(404, "unsupported connector")
    return {"provider": provider, "status": "QUEUED", "mode": "dry-run"}


@router.post("/connectors/outlook/webhook")
async def outlook_webhook_validation(
    validationToken: Annotated[str | None, Query()] = None,
) -> Response:  # noqa: N803
    if validationToken is not None:
        return Response(validationToken, media_type="text/plain")
    return Response(status_code=202)


class ZaloPreviewRequest(BaseModel):
    recipient_id: str
    verified: bool
    consented: bool
    suppressed: bool = False
    is_group: bool = False
    template_id: str
    template_version: int = Field(ge=1)
    locale: str = "vi-VN"
    allowed_variables: list[str]
    variables: dict[str, str]
    contains_sensitive_detail: bool = False
    local_hour: int = Field(ge=0, le=23)


@router.post("/zalo/preview")
async def zalo_preview(
    request: ZaloPreviewRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.APPROVAL_SINGLE))],
) -> dict[str, object]:
    del actor
    try:
        preview = preview_zalo_notification(
            template=ZaloTemplate(
                request.template_id,
                request.template_version,
                request.locale,
                frozenset(request.allowed_variables),
                request.contains_sensitive_detail,
            ),
            recipient=ZaloRecipient(
                request.recipient_id,
                request.verified,
                request.consented,
                request.is_group,
                request.suppressed,
            ),
            variables=request.variables,
            now_local=time(request.local_hour),
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "recipient_id": preview.recipient_id,
        "template_id": preview.template_id,
        "template_version": preview.template_version,
        "variables": preview.variables,
        "dry_run": preview.dry_run,
        "policy_checks": preview.policy_checks,
        "status": "PREVIEWED",
    }


class BulkPreviewRequest(BaseModel):
    items: list[BulkItem]


@router.post("/approvals/bulk/preview")
async def bulk_preview(
    request: BulkPreviewRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.APPROVAL_BULK))],
) -> dict[str, object]:
    del actor
    try:
        result = preview_bulk(request.items)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "eligible": [str(item.approval_id) for item in result.eligible],
        "excluded": [{"id": str(item_id), "reason": reason} for item_id, reason in result.excluded],
        "total_minor": result.total_minor,
        "channel": result.channel,
    }


class BulkCommitItemRequest(BaseModel):
    approval_id: UUID
    expected_case_version: int = Field(ge=1)
    content: str


class BulkCommitRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=300)
    items: list[BulkCommitItemRequest] = Field(min_length=1, max_length=100)


@router.post("/approvals/bulk/commit")
async def bulk_commit(
    request: BulkCommitRequest,
    actor: Annotated[Actor, Depends(require_permission(Permission.APPROVAL_BULK))],
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        existing = session.scalar(
            select(BulkApprovalBatch).where(
                BulkApprovalBatch.tenant_id == actor.tenant_id,
                BulkApprovalBatch.idempotency_key == request.idempotency_key,
            )
        )
        if existing is not None:
            return {"batch_id": str(existing.id), "status": existing.status, **existing.summary}
        batch = BulkApprovalBatch(
            tenant_id=actor.tenant_id,
            idempotency_key=request.idempotency_key,
            created_by=actor.user_id,
            status="PROCESSING",
            filter_snapshot={"selection": "explicit", "count": len(request.items)},
            summary={},
        )
        session.add(batch)
        session.flush()
        results: list[dict[str, str]] = []
        approved = excluded = 0
        for item in request.items:
            approval = session.scalar(
                select(Approval)
                .where(
                    Approval.tenant_id == actor.tenant_id,
                    Approval.id == item.approval_id,
                )
                .with_for_update()
            )
            reason: str | None = None
            if approval is None:
                reason = "not_found"
            else:
                case = session.scalar(
                    select(PaymentCase)
                    .where(
                        PaymentCase.tenant_id == actor.tenant_id,
                        PaymentCase.id == approval.case_id,
                    )
                    .with_for_update()
                )
                if case is None:
                    reason = "case_not_found"
                elif case.version != item.expected_case_version:
                    reason = "stale_version"
                elif approval.status != "PENDING":
                    reason = "not_pending"
                else:
                    try:
                        approve_content(
                            session,
                            tenant_id=actor.tenant_id,
                            approval_id=approval.id,
                            actor_id=actor.user_id,
                            role=actor.role,
                            current_content=item.content,
                        )
                    except (PermissionError, ValueError) as exc:
                        reason = str(exc)
            status = "APPROVED" if reason is None else "EXCLUDED"
            approved += reason is None
            excluded += reason is not None
            session.add(
                BulkApprovalItem(
                    tenant_id=actor.tenant_id,
                    batch_id=batch.id,
                    approval_id=item.approval_id,
                    expected_version=item.expected_case_version,
                    status=status,
                    reason=reason,
                )
            )
            results.append(
                {"approval_id": str(item.approval_id), "status": status, "reason": reason or ""}
            )
        batch.status = "COMPLETED_WITH_EXCLUSIONS" if excluded else "COMPLETED"
        batch.summary = {"approved": approved, "excluded": excluded, "results": results}
        return {"batch_id": str(batch.id), "status": batch.status, **batch.summary}


@router.get("/forecast")
async def forecast(
    actor: Annotated[Actor, Depends(require_permission(Permission.CASE_VIEW))],
    as_of: date | None = None,
) -> dict[str, object]:
    snapshot_date = as_of or datetime.now(UTC).date()
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            select(Invoice, Customer)
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(Invoice.tenant_id == actor.tenant_id, Invoice.outstanding_minor > 0)
        ).all()
    inputs = [
        ForecastInvoice(str(invoice.id), invoice.outstanding_minor, invoice.due_date)
        for invoice, _customer in rows
    ]
    points = baseline_forecast(inputs, as_of=snapshot_date)
    return {
        "as_of": snapshot_date.isoformat(),
        "model_version": "deterministic-baseline-v1",
        "advanced_model_enabled": False,
        "warning": "sparse history" if any(item.confidence == "LOW" for item in points) else None,
        "buckets": cashflow_buckets(points, as_of=snapshot_date),
        "predictions": [
            {
                "invoice_id": item.invoice_id,
                "contractual_date": item.contractual_date.isoformat(),
                "expected_date": item.expected_date.isoformat(),
                "expected_minor": item.expected_minor,
                "interval": [item.low_minor, item.high_minor],
                "confidence": item.confidence,
                "provenance": item.provenance,
            }
            for item in points
        ],
    }


@router.get("/llm-analytics")
async def llm_analytics(
    actor: Annotated[Actor, Depends(require_permission(Permission.LLM_DASHBOARD_VIEW))],
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        usage = session.scalars(
            select(LLMUsageEvent).where(LLMUsageEvent.tenant_id == actor.tenant_id).limit(10_000)
        ).all()
        prices = session.scalars(select(LLMPricing)).all()
        quality = session.scalars(
            select(LLMQualityMetric)
            .where(LLMQualityMetric.tenant_id == actor.tenant_id)
            .limit(10_000)
        ).all()
    online = aggregate_online(
        [
            LLMEvent(
                item.provider,
                item.model,
                item.task_type,
                item.prompt_version,
                item.route,
                item.occurred_at,
                item.latency_ms,
                item.success,
                item.schema_valid,
                item.fallback,
                item.input_tokens,
                item.output_tokens,
            )
            for item in usage
        ],
        [
            PricingVersion(
                item.provider,
                item.model,
                item.effective_from,
                item.currency,
                Decimal(item.input_per_million),
                Decimal(item.output_per_million),
                item.version,
            )
            for item in prices
        ],
    )
    return {
        "online_operational": online,
        "offline_quality": [
            {
                "dataset_version": item.dataset_version,
                "task_type": item.task_type,
                "provider": item.provider,
                "model": item.model,
                "metric": item.metric_name,
                "value": item.metric_value,
                "sample_count": item.sample_count,
            }
            for item in quality
        ],
        "redaction": "metadata-only",
    }
