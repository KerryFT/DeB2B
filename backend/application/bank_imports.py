from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.value_objects import Money
from backend.infrastructure.models import BankTransaction


class BankRow(BaseModel):
    external_id: str | None = None
    booked_date: date
    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    reference: str = Field(min_length=1, max_length=500)
    transaction_type: str = Field(default="CREDIT", pattern=r"^(CREDIT|REVERSAL|REFUND)$")
    reversal_of_external_id: str | None = None

    def fingerprint(self) -> str:
        parts = (
            self.external_id or "",
            str(self.booked_date),
            str(self.amount),
            self.currency.upper(),
            self.reference.strip(),
            self.transaction_type,
            self.reversal_of_external_id or "",
        )
        source = "|".join(parts)
        return hashlib.sha256(source.encode()).hexdigest()


class BankPreview(BaseModel):
    valid: list[BankRow]
    invalid: list[dict[str, object]]


def preview_bank_csv(content: bytes) -> BankPreview:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    valid = []
    invalid = []
    for row_number, record in enumerate(reader, start=2):
        try:
            valid.append(BankRow.model_validate(record))
        except ValidationError as exc:
            invalid.append({"row_number": row_number, "errors": exc.errors()})
    return BankPreview(valid=valid, invalid=invalid)


def upsert_bank_rows(session: Session, *, tenant_id: UUID, rows: list[BankRow]) -> tuple[int, int]:
    created = duplicates = 0
    for row in rows:
        existing = session.scalar(
            select(BankTransaction).where(
                BankTransaction.tenant_id == tenant_id,
                BankTransaction.source_fingerprint == row.fingerprint(),
            )
        )
        if existing is not None:
            duplicates += 1
            continue
        amount = Money.from_decimal(row.amount, row.currency)
        session.add(
            BankTransaction(
                tenant_id=tenant_id,
                external_id=row.external_id,
                booked_date=row.booked_date,
                amount_minor=amount.minor_units,
                currency=amount.currency,
                reference=row.reference,
                source_fingerprint=row.fingerprint(),
                transaction_type=row.transaction_type,
            )
        )
        created += 1
    return created, duplicates
