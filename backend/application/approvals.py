from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.permissions import Permission, is_allowed
from backend.infrastructure.models import Approval


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def approve_content(
    session: Session,
    *,
    tenant_id: UUID,
    approval_id: UUID,
    actor_id: UUID,
    role: str,
    current_content: str,
) -> Approval:
    if not is_allowed(role, Permission.APPROVAL_SINGLE):
        raise PermissionError("approval permission required")
    approval = session.scalar(
        select(Approval).where(Approval.tenant_id == tenant_id, Approval.id == approval_id)
    )
    if approval is None:
        raise LookupError("approval not found")
    if approval.expires_at <= datetime.now(UTC):
        raise ValueError("approval expired")
    if approval.content_hash != content_hash(current_content):
        approval.status = "INVALIDATED"
        raise ValueError("content changed after approval request")
    approval.status = "APPROVED"
    approval.decided_by = actor_id
    return approval
