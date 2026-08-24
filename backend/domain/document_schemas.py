from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class EvidenceRef(BaseModel):
    document_id: str
    page: int | None = Field(default=None, ge=1)
    sheet: str | None = None
    cell_range: str | None = None
    quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_location(self) -> EvidenceRef:
        if self.page is None and not (self.sheet and self.cell_range):
            raise ValueError("evidence requires a page or sheet/cell location")
        return self


class InvoiceExtraction(BaseModel):
    invoice_number: str
    customer_tax_id: str | None = None
    issue_date: date
    due_date: date
    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    evidence: dict[str, EvidenceRef]


class ContractExtraction(BaseModel):
    contract_number: str
    customer_name: str
    effective_date: date
    payment_terms_days: int = Field(ge=0, le=3650)
    evidence: dict[str, EvidenceRef]


class PurchaseOrderExtraction(BaseModel):
    po_number: str
    invoice_numbers: list[str]
    total_amount: Decimal = Field(gt=0)
    evidence: dict[str, EvidenceRef]


class AcceptanceExtraction(BaseModel):
    acceptance_number: str
    signed_date: date | None
    buyer_signed: bool
    invoice_numbers: list[str]
    evidence: dict[str, EvidenceRef]


class BankTransactionExtraction(BaseModel):
    transaction_id: str
    booked_date: date
    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    reference: str
    evidence: dict[str, EvidenceRef]
