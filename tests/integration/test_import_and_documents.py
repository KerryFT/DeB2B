from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.application.documents import quarantine_and_store
from backend.application.imports import preview_import
from backend.application.invoice_import_service import upsert_invoice_rows
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.fakes import FakeMalwareScanner, MemoryObjectStorage
from backend.infrastructure.models import (
    CaseInvoice,
    Customer,
    Document,
    DocumentSource,
    Invoice,
    PaymentCase,
    Tenant,
)


def test_invoice_reimport_is_idempotent_and_money_is_exact() -> None:
    tenant_id = uuid4()
    content = Path("data/fixtures/smoke-v1/invoices.csv").read_bytes()
    rows = preview_import(content, "invoices.csv").valid
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Import test"))
        session.flush()
        first = upsert_invoice_rows(
            session,
            tenant_id=tenant_id,
            rows=rows,
            correlation_id="import-1",
            actor_id="test",
        )
    with SessionFactory.begin() as session:
        second = upsert_invoice_rows(
            session,
            tenant_id=tenant_id,
            rows=rows,
            correlation_id="import-2",
            actor_id="test",
        )
        assert (
            session.scalar(
                select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)
            )
            == 6
        )
        assert (
            session.scalar(
                select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant_id)
            )
            == 10
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(PaymentCase)
                .where(PaymentCase.tenant_id == tenant_id)
            )
            == 10
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(CaseInvoice)
                .where(CaseInvoice.tenant_id == tenant_id)
            )
            == 10
        )
        assert session.scalar(
            select(func.sum(Invoice.amount_minor)).where(Invoice.tenant_id == tenant_id)
        ) == sum(int(row.amount) for row in rows)
    assert first.invoices_created == 10
    assert second.invoices_created == 0
    assert second.invoices_updated == 10


@pytest.mark.asyncio
async def test_document_hash_reuses_object_and_malware_is_rejected() -> None:
    tenant_id = uuid4()
    storage = MemoryObjectStorage()
    scanner = FakeMalwareScanner()
    png = b"\x89PNG\r\n\x1a\nsynthetic-image"
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Document test"))
        session.flush()
        first = await quarantine_and_store(
            session,
            tenant_id=tenant_id,
            content=png,
            filename="invoice.png",
            content_type="image/png",
            scanner=scanner,
            storage=storage,
        )
        second = await quarantine_and_store(
            session,
            tenant_id=tenant_id,
            content=png,
            filename="renamed.png",
            content_type="image/png",
            scanner=scanner,
            storage=storage,
        )
        assert (
            session.scalar(
                select(func.count()).select_from(Document).where(Document.tenant_id == tenant_id)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(DocumentSource)
                .where(DocumentSource.tenant_id == tenant_id)
            )
            == 2
        )
    assert first.document_id == second.document_id
    assert second.reused is True
    assert scanner.calls == 1
    assert len(storage.objects) == 1

    infected = FakeMalwareScanner(clean=False)
    with SessionFactory.begin() as session, pytest.raises(ValueError, match="malware"):
        await quarantine_and_store(
            session,
            tenant_id=tenant_id,
            content=b"\x89PNG\r\n\x1a\nnew-infected",
            filename="infected.png",
            content_type="image/png",
            scanner=infected,
            storage=storage,
        )
