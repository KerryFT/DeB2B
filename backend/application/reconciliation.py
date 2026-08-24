from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.infrastructure.models import (
    BankTransaction,
    CaseInvoice,
    Invoice,
    PaymentAllocation,
    PaymentCase,
)


@dataclass(frozen=True, slots=True)
class AllocationSpec:
    invoice_id: UUID
    amount_minor: int


def confirm_allocations(
    session: Session,
    *,
    tenant_id: UUID,
    transaction_id: UUID,
    allocations: list[AllocationSpec],
    actor_id: UUID,
) -> list[PaymentAllocation]:
    if not allocations or any(item.amount_minor <= 0 for item in allocations):
        raise ValueError("positive allocations are required")
    if len({item.invoice_id for item in allocations}) != len(allocations):
        raise ValueError("duplicate invoice allocation")
    transaction = session.scalar(
        select(BankTransaction)
        .where(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.id == transaction_id,
        )
        .with_for_update()
    )
    if transaction is None:
        raise LookupError("bank transaction not found")
    already_allocated = int(
        session.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount_minor), 0)).where(
                PaymentAllocation.tenant_id == tenant_id,
                PaymentAllocation.transaction_id == transaction_id,
                PaymentAllocation.status == "CONFIRMED",
            )
        )
        or 0
    )
    requested = sum(item.amount_minor for item in allocations)
    if already_allocated + requested > transaction.amount_minor:
        raise ValueError("allocations exceed transaction amount")
    created = []
    affected_cases: set[UUID] = set()
    for item in allocations:
        invoice = session.scalar(
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id, Invoice.id == item.invoice_id)
            .with_for_update()
        )
        if invoice is None:
            raise LookupError("invoice not found")
        if item.amount_minor > invoice.outstanding_minor:
            raise ValueError("allocation exceeds invoice outstanding")
        invoice.outstanding_minor -= item.amount_minor
        allocation = PaymentAllocation(
            tenant_id=tenant_id,
            transaction_id=transaction_id,
            invoice_id=invoice.id,
            amount_minor=item.amount_minor,
            status="CONFIRMED",
            confirmed_by=actor_id,
        )
        session.add(allocation)
        created.append(allocation)
        affected_cases.update(
            session.scalars(
                select(CaseInvoice.case_id).where(
                    CaseInvoice.tenant_id == tenant_id, CaseInvoice.invoice_id == invoice.id
                )
            )
        )
    session.flush()
    total = already_allocated + requested
    transaction.status = "MATCHED" if total == transaction.amount_minor else "PARTIALLY_MATCHED"
    for case_id in affected_cases:
        remaining = session.scalar(
            select(func.sum(Invoice.outstanding_minor))
            .join(CaseInvoice, CaseInvoice.invoice_id == Invoice.id)
            .where(CaseInvoice.tenant_id == tenant_id, CaseInvoice.case_id == case_id)
        )
        if remaining == 0:
            case = session.scalar(
                select(PaymentCase)
                .where(PaymentCase.tenant_id == tenant_id, PaymentCase.id == case_id)
                .with_for_update()
            )
            if case is not None:
                case.status = "PAID"
    return created
