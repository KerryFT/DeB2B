from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import (
    AuditEntry,
    CaseDocument,
    Document,
    EvidenceSpan,
    PaymentCase,
    Tenant,
)
from services.api.main import app

HEADERS = {
    "x-dev-user-id": "00000000-0000-0000-0000-000000000002",
    "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001",
    "x-dev-role": "operator",
}


def test_import_preview_commit_and_case_list() -> None:
    content = Path("data/fixtures/smoke-v1/invoices.xlsx").read_bytes()
    with TestClient(app) as client:
        preview = client.post(
            "/api/v1/imports/preview",
            headers=HEADERS,
            files={"file": ("invoices.xlsx", content)},
        )
        assert preview.status_code == 200
        assert len(preview.json()["valid"]) == 10
        assert preview.json()["invalid"] == []

        commit = client.post(
            "/api/v1/imports/commit",
            headers=HEADERS,
            files={"file": ("invoices.xlsx", content)},
        )
        assert commit.status_code == 200
        assert commit.json()["invoices_created"] == 0
        assert commit.json()["invoices_updated"] == 10

        cases = client.get("/api/v1/cases", headers=HEADERS)
        assert cases.status_code == 200
        assert len(cases.json()) == 10


def test_manual_evidence_correction_is_tenant_scoped_and_audited() -> None:
    tenant_id, user_id = uuid4(), uuid4()
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Evidence correction"))
        session.flush()
        case = PaymentCase(tenant_id=tenant_id)
        document = Document(
            tenant_id=tenant_id,
            sha256="a" * 64,
            object_key=f"{tenant_id}/sha256/{'a' * 64}",
            filename="evidence.png",
            content_type="image/png",
        )
        session.add_all([case, document])
        session.flush()
        session.add(CaseDocument(tenant_id=tenant_id, case_id=case.id, document_id=document.id))
        span = EvidenceSpan(
            tenant_id=tenant_id,
            document_id=document.id,
            field_name="invoice_number",
            page=1,
            sheet=None,
            cell_range=None,
            polygon=None,
            quote="INV-OO1",
        )
        session.add(span)
        session.flush()
        evidence_id = span.id
    headers = {
        "x-dev-user-id": str(user_id),
        "x-dev-tenant-id": str(tenant_id),
        "x-dev-role": "operator",
    }
    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/evidence/{evidence_id}",
            headers=headers,
            json={"quote": "INV-001", "page": 1},
        )
    assert response.status_code == 200
    with SessionFactory() as session:
        assert session.get(EvidenceSpan, evidence_id).quote == "INV-001"
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEntry)
                .where(AuditEntry.tenant_id == tenant_id, AuditEntry.action == "EVIDENCE_CORRECTED")
            )
            == 1
        )
