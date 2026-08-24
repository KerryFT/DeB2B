from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.infrastructure import models

TENANT_MODELS = (
    models.Customer,
    models.Invoice,
    models.PaymentCase,
    models.Document,
    models.Communication,
    models.BankTransaction,
    models.AuditEntry,
)


def export_tenant_manifest(session: Session, *, tenant_id: UUID) -> dict[str, Any]:
    counts = {
        model.__tablename__: int(
            session.scalar(
                select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
            )
            or 0
        )
        for model in TENANT_MODELS
    }
    documents = session.execute(
        select(models.Document.object_key, models.Document.sha256).where(
            models.Document.tenant_id == tenant_id
        )
    ).all()
    manifest: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "counts": counts,
        "objects": [{"key": key, "sha256": digest} for key, digest in documents],
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return manifest


@dataclass(frozen=True, slots=True)
class TenantDeletionResult:
    deleted_rows: int
    object_keys: tuple[str, ...]


def delete_tenant_rows(
    session: Session, *, tenant_id: UUID, approved: bool
) -> TenantDeletionResult:
    if not approved:
        raise PermissionError("tenant deletion requires explicit admin approval")
    object_keys = tuple(
        session.scalars(
            select(models.Document.object_key).where(models.Document.tenant_id == tenant_id)
        )
    )
    deletion_order = (
        models.PaymentAllocation,
        models.FailureRecord,
        models.CommunicationAttachment,
        models.EvidenceSpan,
        models.CaseDocument,
        models.DocumentSource,
        models.Blocker,
        models.DraftAction,
        models.Approval,
        models.CaseInvoice,
        models.Communication,
        models.BankTransaction,
        models.Invoice,
        models.Customer,
        models.PaymentCase,
        models.Document,
        models.ConnectorCursor,
        models.ConnectorCredential,
        models.IdempotencyRecord,
        models.OutboxEvent,
        models.AuditEntry,
        models.Membership,
    )
    deleted = 0
    for model in deletion_order:
        result = session.execute(delete(model).where(model.tenant_id == tenant_id))
        deleted += int(result.rowcount or 0)  # type: ignore[attr-defined]
    tenant_result = session.execute(delete(models.Tenant).where(models.Tenant.id == tenant_id))
    deleted += int(tenant_result.rowcount or 0)  # type: ignore[attr-defined]
    return TenantDeletionResult(deleted, object_keys)
