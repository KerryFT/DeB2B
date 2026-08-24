from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

import structlog
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel
from sqlalchemy import func, select, text

from backend.application.approvals import approve_content
from backend.application.bank_imports import BankPreview, preview_bank_csv, upsert_bank_rows
from backend.application.documents import quarantine_and_store
from backend.application.imports import ImportPreview, preview_import
from backend.application.invoice_import_service import ImportResult, upsert_invoice_rows
from backend.application.mutation import MutationContext, record_mutation
from backend.application.reconciliation import AllocationSpec, confirm_allocations
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import SessionFactory, tenant_session
from backend.infrastructure.fakes import FakeMalwareScanner, MemoryObjectStorage
from backend.infrastructure.models import (
    Approval,
    AuditEntry,
    BankTransaction,
    Blocker,
    CaseDocument,
    CaseInvoice,
    Customer,
    EvidenceSpan,
    Invoice,
    PaymentCase,
)
from services.api.auth import Actor, current_actor, require_roles

logger = structlog.get_logger()
development_storage = MemoryObjectStorage()
development_scanner = FakeMalwareScanner()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    logger.info("api_started", environment=get_settings().app_env)
    yield


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "authorization",
        "content-type",
        "x-correlation-id",
        "x-dev-role",
        "x-dev-tenant-id",
        "x-dev-user-id",
    ],
)
REQUESTS = Counter("ar_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("ar_http_request_seconds", "HTTP request latency", ["method", "path"])
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def request_observability(request: Request, call_next):  # type: ignore[no-untyped-def]
    correlation_id = request.headers.get("x-correlation-id", str(uuid4()))[:100]
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id,
        )
        raise
    elapsed = perf_counter() - started
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(request.method, path).observe(elapsed)
    response.headers["x-correlation-id"] = correlation_id
    logger.info(
        "request_completed",
        method=request.method,
        path=path,
        status=response.status_code,
        latency_ms=round(elapsed * 1000),
        correlation_id=correlation_id,
    )
    return response


class Health(BaseModel):
    status: str


@app.get("/live", response_model=Health)
async def live() -> Health:
    return Health(status="ok")


@app.get("/ready", response_model=Health)
async def ready() -> Health:
    with SessionFactory() as session:
        session.execute(text("SELECT 1"))
    return Health(status="ok")


@app.get("/api/v1/me")
async def me(actor: Annotated[Actor, Depends(current_actor)]) -> dict[str, str]:
    return {"user_id": str(actor.user_id), "tenant_id": str(actor.tenant_id), "role": actor.role}


@app.post("/api/v1/imports/preview", response_model=ImportPreview)
async def import_preview(
    actor: Annotated[Actor, Depends(require_roles("operator", "admin"))],
    file: Annotated[UploadFile, File()],
) -> ImportPreview:
    del actor
    try:
        return preview_import(await file.read(), file.filename or "upload.csv")
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/v1/imports/commit", response_model=ImportResult)
async def import_commit(
    request: Request,
    actor: Annotated[Actor, Depends(require_roles("operator", "admin"))],
    file: Annotated[UploadFile, File()],
) -> ImportResult:
    try:
        preview = preview_import(await file.read(), file.filename or "upload.csv")
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if preview.invalid:
        raise HTTPException(422, "commit requires a preview with zero invalid rows")
    with tenant_session(actor.tenant_id) as session:
        return upsert_invoice_rows(
            session,
            tenant_id=actor.tenant_id,
            rows=preview.valid,
            correlation_id=request.headers.get("x-correlation-id", str(uuid4()))[:100],
            actor_id=str(actor.user_id),
        )


@app.post("/api/v1/documents")
async def upload_document(
    actor: Annotated[Actor, Depends(require_roles("operator", "admin"))],
    file: Annotated[UploadFile, File()],
    case_id: Annotated[UUID | None, Form()] = None,
) -> dict[str, str | bool]:
    content = await file.read()
    with tenant_session(actor.tenant_id) as session:
        try:
            stored = await quarantine_and_store(
                session,
                tenant_id=actor.tenant_id,
                content=content,
                filename=file.filename or "upload",
                content_type=file.content_type or "application/octet-stream",
                scanner=development_scanner,
                storage=development_storage,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if case_id is not None:
            case = session.scalar(
                select(PaymentCase).where(
                    PaymentCase.tenant_id == actor.tenant_id, PaymentCase.id == case_id
                )
            )
            if case is None:
                raise HTTPException(404, "case not found")
            linked = session.scalar(
                select(CaseDocument).where(
                    CaseDocument.tenant_id == actor.tenant_id,
                    CaseDocument.case_id == case_id,
                    CaseDocument.document_id == stored.document_id,
                )
            )
            if linked is None:
                session.add(
                    CaseDocument(
                        tenant_id=actor.tenant_id,
                        case_id=case_id,
                        document_id=stored.document_id,
                    )
                )
    return {
        "document_id": str(stored.document_id),
        "object_key": stored.object_key,
        "reused": stored.reused,
    }


@app.get("/api/v1/cases")
async def list_cases(
    actor: Annotated[Actor, Depends(current_actor)],
) -> list[dict[str, str | int]]:
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            select(PaymentCase, Invoice, Customer)
            .join(CaseInvoice, CaseInvoice.case_id == PaymentCase.id)
            .join(Invoice, Invoice.id == CaseInvoice.invoice_id)
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(PaymentCase.tenant_id == actor.tenant_id)
            .order_by(Invoice.due_date)
            .limit(100)
        ).all()
    return [
        {
            "id": str(case.id),
            "status": case.status,
            "invoice_number": invoice.invoice_number,
            "customer": customer.name,
            "outstanding_minor": invoice.outstanding_minor,
            "currency": invoice.currency,
        }
        for case, invoice, customer in rows
    ]


@app.get("/api/v1/cases/{case_id}")
async def case_detail(
    case_id: UUID,
    actor: Annotated[Actor, Depends(current_actor)],
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        case = session.scalar(
            select(PaymentCase).where(
                PaymentCase.tenant_id == actor.tenant_id, PaymentCase.id == case_id
            )
        )
        if case is None:
            raise HTTPException(404, "case not found")
        invoices = session.scalars(
            select(Invoice)
            .join(CaseInvoice, CaseInvoice.invoice_id == Invoice.id)
            .where(CaseInvoice.tenant_id == actor.tenant_id, CaseInvoice.case_id == case_id)
        ).all()
        blockers = session.scalars(
            select(Blocker).where(Blocker.tenant_id == actor.tenant_id, Blocker.case_id == case_id)
        ).all()
        approvals = session.scalars(
            select(Approval).where(
                Approval.tenant_id == actor.tenant_id, Approval.case_id == case_id
            )
        ).all()
        evidence = session.scalars(
            select(EvidenceSpan)
            .join(CaseDocument, CaseDocument.document_id == EvidenceSpan.document_id)
            .where(CaseDocument.tenant_id == actor.tenant_id, CaseDocument.case_id == case_id)
        ).all()
        timeline = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.tenant_id == actor.tenant_id, AuditEntry.aggregate_id == case_id)
            .order_by(AuditEntry.occurred_at)
        ).all()
        return {
            "id": str(case.id),
            "status": case.status,
            "version": case.version,
            "invoices": [
                {
                    "id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "outstanding_minor": invoice.outstanding_minor,
                    "currency": invoice.currency,
                }
                for invoice in invoices
            ],
            "blockers": [
                {"type": blocker.blocker_type, "active": blocker.active} for blocker in blockers
            ],
            "approvals": [
                {"id": str(approval.id), "status": approval.status} for approval in approvals
            ],
            "evidence": [
                {
                    "field": span.field_name,
                    "page": span.page,
                    "sheet": span.sheet,
                    "cell_range": span.cell_range,
                    "quote": span.quote,
                }
                for span in evidence
            ],
            "timeline": [
                {
                    "action": entry.action,
                    "occurred_at": entry.occurred_at.isoformat(),
                    "payload": entry.payload,
                }
                for entry in timeline
            ],
        }


class ApprovalDecision(BaseModel):
    content: str


@app.post("/api/v1/approvals/{approval_id}/approve")
async def approve(
    approval_id: UUID,
    decision: ApprovalDecision,
    actor: Annotated[Actor, Depends(require_roles("approver", "admin"))],
) -> dict[str, str]:
    with tenant_session(actor.tenant_id) as session:
        try:
            approval = approve_content(
                session,
                tenant_id=actor.tenant_id,
                approval_id=approval_id,
                actor_id=actor.user_id,
                role=actor.role,
                current_content=decision.content,
            )
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except (PermissionError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"id": str(approval.id), "status": approval.status}


class EvidenceCorrection(BaseModel):
    quote: str
    page: int | None = None
    sheet: str | None = None
    cell_range: str | None = None


@app.patch("/api/v1/evidence/{evidence_id}")
async def correct_evidence(
    evidence_id: UUID,
    correction: EvidenceCorrection,
    actor: Annotated[Actor, Depends(require_roles("operator", "approver", "admin"))],
) -> dict[str, str]:
    if correction.page is None and not (correction.sheet and correction.cell_range):
        raise HTTPException(422, "evidence requires page or sheet/cell")
    with tenant_session(actor.tenant_id) as session:
        span = session.scalar(
            select(EvidenceSpan).where(
                EvidenceSpan.tenant_id == actor.tenant_id, EvidenceSpan.id == evidence_id
            )
        )
        if span is None:
            raise HTTPException(404, "evidence not found")
        before = {
            "quote": span.quote,
            "page": span.page,
            "sheet": span.sheet,
            "cell_range": span.cell_range,
        }
        span.quote = correction.quote
        span.page = correction.page
        span.sheet = correction.sheet
        span.cell_range = correction.cell_range
        record_mutation(
            session,
            context=MutationContext(actor.tenant_id, "USER", str(actor.user_id), str(uuid4())),
            action="EVIDENCE_CORRECTED",
            aggregate_type="EVIDENCE",
            aggregate_id=span.id,
            audit_payload={"before": before, "after": correction.model_dump()},
            event_topic="evidence.corrected.v1",
            event_payload={"evidence_id": str(span.id)},
        )
        return {"id": str(span.id), "status": "CORRECTED"}


@app.post("/api/v1/bank-imports/preview", response_model=BankPreview)
async def bank_preview(
    actor: Annotated[Actor, Depends(require_roles("operator", "admin"))],
    file: Annotated[UploadFile, File()],
) -> BankPreview:
    del actor
    try:
        return preview_bank_csv(await file.read())
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "bank CSV must be UTF-8") from exc


@app.post("/api/v1/bank-imports/commit")
async def bank_commit(
    actor: Annotated[Actor, Depends(require_roles("operator", "admin"))],
    file: Annotated[UploadFile, File()],
) -> dict[str, int]:
    preview = preview_bank_csv(await file.read())
    if preview.invalid:
        raise HTTPException(422, "commit requires zero invalid rows")
    with tenant_session(actor.tenant_id) as session:
        created, duplicates = upsert_bank_rows(
            session, tenant_id=actor.tenant_id, rows=preview.valid
        )
    return {"created": created, "duplicates": duplicates}


class AllocationRequest(BaseModel):
    transaction_id: UUID
    allocations: list[AllocationSpec]


@app.post("/api/v1/reconciliation/confirm")
async def reconciliation_confirm(
    request: AllocationRequest,
    actor: Annotated[Actor, Depends(require_roles("approver", "admin"))],
) -> dict[str, int]:
    with tenant_session(actor.tenant_id) as session:
        try:
            confirmed = confirm_allocations(
                session,
                tenant_id=actor.tenant_id,
                transaction_id=request.transaction_id,
                allocations=request.allocations,
                actor_id=actor.user_id,
            )
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
    return {"confirmed": len(confirmed)}


@app.get("/api/v1/reconciliation")
async def reconciliation_queue(
    actor: Annotated[Actor, Depends(current_actor)],
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        transactions = session.scalars(
            select(BankTransaction)
            .where(BankTransaction.tenant_id == actor.tenant_id)
            .order_by(BankTransaction.booked_date.desc())
            .limit(100)
        ).all()
        return [
            {
                "id": str(item.id),
                "booked_date": item.booked_date.isoformat(),
                "amount_minor": item.amount_minor,
                "currency": item.currency,
                "reference": item.reference,
                "status": item.status,
            }
            for item in transactions
        ]


@app.get("/api/v1/dashboard")
async def dashboard(actor: Annotated[Actor, Depends(current_actor)]) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        outstanding = session.scalar(
            select(func.coalesce(func.sum(Invoice.outstanding_minor), 0)).where(
                Invoice.tenant_id == actor.tenant_id
            )
        )
        open_cases = session.scalar(
            select(func.count())
            .select_from(PaymentCase)
            .where(
                PaymentCase.tenant_id == actor.tenant_id,
                PaymentCase.status.not_in(("PAID", "CLOSED", "CANCELLED")),
            )
        )
        active_blockers = session.scalar(
            select(func.count())
            .select_from(Blocker)
            .where(Blocker.tenant_id == actor.tenant_id, Blocker.active.is_(True))
        )
    return {
        "outstanding_minor": int(outstanding or 0),
        "currency": "VND",
        "open_cases": int(open_cases or 0),
        "active_blockers": int(active_blockers or 0),
        "as_of": datetime.now(UTC).isoformat(),
    }
