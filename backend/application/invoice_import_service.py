from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.imports import InvoiceImportRow
from backend.application.mutation import MutationContext, record_mutation
from backend.domain.value_objects import Money
from backend.infrastructure.models import CaseInvoice, Customer, Invoice, PaymentCase


@dataclass(frozen=True, slots=True)
class ImportResult:
    customers_created: int
    invoices_created: int
    invoices_updated: int
    cases_created: int


def upsert_invoice_rows(
    session: Session,
    *,
    tenant_id: UUID,
    rows: list[InvoiceImportRow],
    correlation_id: str,
    actor_id: str | None,
) -> ImportResult:
    """Upsert a validated batch in the caller's transaction."""
    customer_count = invoice_count = updated_count = case_count = 0
    context = MutationContext(tenant_id, "USER", actor_id, correlation_id)
    for row in rows:
        customer = session.scalar(
            select(Customer).where(
                Customer.tenant_id == tenant_id, Customer.code == row.customer_code
            )
        )
        if customer is None:
            customer = Customer(
                tenant_id=tenant_id,
                code=row.customer_code,
                name=row.customer_name,
                tax_id=row.tax_id,
            )
            session.add(customer)
            session.flush()
            customer_count += 1
        else:
            customer.name = row.customer_name
            customer.tax_id = row.tax_id

        amount = Money.from_decimal(row.amount, row.currency)
        outstanding = Money.from_decimal(row.outstanding_amount, row.currency)
        invoice = session.scalar(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id, Invoice.source_fingerprint == row.fingerprint()
            )
        )
        if invoice is None:
            invoice = Invoice(
                tenant_id=tenant_id,
                customer_id=customer.id,
                invoice_number=row.invoice_number,
                issue_date=row.issue_date,
                due_date=row.due_date,
                amount_minor=amount.minor_units,
                outstanding_minor=outstanding.minor_units,
                currency=amount.currency,
                source_fingerprint=row.fingerprint(),
                account_owner=row.account_owner,
            )
            session.add(invoice)
            session.flush()
            invoice_count += 1
            case = PaymentCase(tenant_id=tenant_id)
            session.add(case)
            session.flush()
            session.add(
                CaseInvoice(
                    tenant_id=tenant_id,
                    case_id=case.id,
                    invoice_id=invoice.id,
                )
            )
            case_count += 1
            record_mutation(
                session,
                context=context,
                action="INVOICE_IMPORTED",
                aggregate_type="INVOICE",
                aggregate_id=invoice.id,
                audit_payload={"fingerprint": row.fingerprint()},
                event_topic="invoice.imported.v1",
                event_payload={"invoice_id": str(invoice.id), "case_id": str(case.id)},
            )
        else:
            invoice.customer_id = customer.id
            invoice.due_date = row.due_date
            invoice.amount_minor = amount.minor_units
            invoice.outstanding_minor = outstanding.minor_units
            invoice.account_owner = row.account_owner
            updated_count += 1
    return ImportResult(customer_count, invoice_count, updated_count, case_count)
