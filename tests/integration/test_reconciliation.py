from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.application.bank_imports import preview_bank_csv, upsert_bank_rows
from backend.application.reconciliation import AllocationSpec, confirm_allocations
from backend.domain.payment_matching import (
    OpenInvoice,
    choose_payment_candidate,
    payment_candidates,
)
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import (
    BankTransaction,
    CaseInvoice,
    Customer,
    Invoice,
    PaymentCase,
    Tenant,
)


def test_bank_import_matching_and_confirmed_paid_transition() -> None:
    tenant_id, actor_id = uuid4(), uuid4()
    preview = preview_bank_csv(Path("data/fixtures/smoke-v1/bank.csv").read_bytes())
    assert not preview.invalid
    row = preview.valid[0]
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Bank reconciliation"))
        session.flush()
        customer = Customer(tenant_id=tenant_id, code="C1", name="Synthetic", tax_id=None)
        session.add(customer)
        session.flush()
        invoice = Invoice(
            tenant_id=tenant_id,
            customer_id=customer.id,
            invoice_number="INV-2026-0001",
            issue_date=row.booked_date,
            due_date=row.booked_date,
            amount_minor=int(row.amount),
            outstanding_minor=int(row.amount),
            currency="VND",
            source_fingerprint="b" * 64,
        )
        case = PaymentCase(tenant_id=tenant_id, status="RECONCILIATION_REVIEW")
        session.add_all([invoice, case])
        session.flush()
        session.add(CaseInvoice(tenant_id=tenant_id, case_id=case.id, invoice_id=invoice.id))
        created, duplicates = upsert_bank_rows(session, tenant_id=tenant_id, rows=[row])
        assert (created, duplicates) == (1, 0)
        session.flush()
        transaction = session.scalar(
            select(BankTransaction).where(BankTransaction.tenant_id == tenant_id)
        )
        assert transaction is not None
        candidate = choose_payment_candidate(
            payment_candidates(
                amount_minor=transaction.amount_minor,
                reference=transaction.reference,
                invoices=[
                    OpenInvoice(invoice.id, invoice.invoice_number, invoice.outstanding_minor)
                ],
            )
        )
        assert candidate is not None
        confirm_allocations(
            session,
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            allocations=[AllocationSpec(invoice.id, transaction.amount_minor)],
            actor_id=actor_id,
        )
        assert invoice.outstanding_minor == 0
        assert case.status == "PAID"


def test_bank_preview_isolates_bad_row_and_ambiguous_amount_abstains() -> None:
    preview = preview_bank_csv(b"booked_date,amount,currency,reference\n2026-08-01,-1,VND,bad\n")
    assert len(preview.invalid) == 1
    amount = 100
    candidates = payment_candidates(
        amount_minor=amount,
        reference="unknown",
        invoices=[OpenInvoice(uuid4(), "INV-1", amount), OpenInvoice(uuid4(), "INV-2", amount)],
    )
    assert choose_payment_candidate(candidates) is None


def test_allocation_cannot_exceed_transaction_amount() -> None:
    tenant_id, actor_id = uuid4(), uuid4()
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Invariant"))
        session.flush()
        customer = Customer(tenant_id=tenant_id, code="C2", name="Synthetic", tax_id=None)
        session.add(customer)
        session.flush()
        invoice = Invoice(
            tenant_id=tenant_id,
            customer_id=customer.id,
            invoice_number="INV-X",
            issue_date=preview_date,
            due_date=preview_date,
            amount_minor=200,
            outstanding_minor=200,
            currency="VND",
            source_fingerprint="c" * 64,
        )
        transaction = BankTransaction(
            tenant_id=tenant_id,
            booked_date=preview_date,
            amount_minor=100,
            currency="VND",
            reference="INV-X",
            source_fingerprint="d" * 64,
        )
        session.add_all([invoice, transaction])
        session.flush()
        with pytest.raises(ValueError, match="transaction amount"):
            confirm_allocations(
                session,
                tenant_id=tenant_id,
                transaction_id=transaction.id,
                allocations=[AllocationSpec(invoice.id, 101)],
                actor_id=actor_id,
            )


preview_date = date(2026, 8, 1)
