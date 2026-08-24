from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.file_policy import AcceptedUpload, validate_upload
from backend.application.ports import ObjectStorage
from backend.infrastructure.models import Document, DocumentSource


class MalwareScanner(Protocol):
    async def is_clean(self, content: bytes) -> bool: ...


@dataclass(frozen=True, slots=True)
class StoredDocument:
    document_id: UUID
    object_key: str
    reused: bool


async def quarantine_and_store(
    session: Session,
    *,
    tenant_id: UUID,
    content: bytes,
    filename: str,
    content_type: str,
    scanner: MalwareScanner,
    storage: ObjectStorage,
) -> StoredDocument:
    accepted: AcceptedUpload = validate_upload(
        content, filename=filename, content_type=content_type
    )
    existing = session.scalar(
        select(Document).where(Document.tenant_id == tenant_id, Document.sha256 == accepted.sha256)
    )
    if existing is not None:
        session.add(
            DocumentSource(
                tenant_id=tenant_id,
                document_id=existing.id,
                filename=accepted.safe_name,
                source_type="UPLOAD",
            )
        )
        return StoredDocument(existing.id, existing.object_key, True)
    if not await scanner.is_clean(content):
        raise ValueError("malware scan rejected upload")
    object_key = await storage.put(
        tenant_id=str(tenant_id),
        key=f"sha256/{accepted.sha256}",
        content=content,
        content_type=content_type,
    )
    document = Document(
        tenant_id=tenant_id,
        sha256=accepted.sha256,
        object_key=object_key,
        filename=accepted.safe_name,
        content_type=content_type,
        pipeline_version="native-v1",
    )
    session.add(document)
    session.flush()
    session.add(
        DocumentSource(
            tenant_id=tenant_id,
            document_id=document.id,
            filename=accepted.safe_name,
            source_type="UPLOAD",
        )
    )
    return StoredDocument(document.id, object_key, False)
