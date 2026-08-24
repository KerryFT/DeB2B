from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.application.tenant_lifecycle import delete_tenant_rows, export_tenant_manifest
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import Document, Tenant


def test_export_and_approved_delete_drill_accounts_for_object_keys() -> None:
    tenant_id = uuid4()
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Disposable deletion drill"))
        session.flush()
        session.add(
            Document(
                tenant_id=tenant_id,
                sha256="e" * 64,
                object_key=f"{tenant_id}/sha256/{'e' * 64}",
                filename="disposable.pdf",
                content_type="application/pdf",
            )
        )
    with SessionFactory.begin() as session:
        manifest = export_tenant_manifest(session, tenant_id=tenant_id)
        assert manifest["counts"]["documents"] == 1
        assert len(manifest["objects"]) == 1
        with pytest.raises(PermissionError):
            delete_tenant_rows(session, tenant_id=tenant_id, approved=False)
        result = delete_tenant_rows(session, tenant_id=tenant_id, approved=True)
        assert result.object_keys == (f"{tenant_id}/sha256/{'e' * 64}",)
    with SessionFactory() as session:
        assert session.scalar(select(Tenant).where(Tenant.id == tenant_id)) is None
