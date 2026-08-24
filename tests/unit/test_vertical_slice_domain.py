from decimal import Decimal
from pathlib import Path
from uuid import UUID

from backend.application.native_extraction import extract_invoice_xlsx
from backend.domain.blocker_engine import classify_missing_documents
from backend.domain.blockers import BlockerType
from backend.domain.matching import choose_unambiguous, rank_invoice_candidates


def test_native_xlsx_extraction_retains_cell_evidence() -> None:
    fields = extract_invoice_xlsx(
        Path("data/fixtures/smoke-v1/invoices.xlsx").read_bytes(), row_number=2
    )
    evidence = {field.name: field for field in fields}
    assert evidence["invoice_number"].value == "INV-2026-0001"
    assert evidence["invoice_number"].cell_range == "A2"
    assert evidence["amount"].cell_range == "G2"


def test_matching_is_explained_and_abstains_on_tie() -> None:
    first = UUID(int=1)
    second = UUID(int=2)
    ranked = rank_invoice_candidates(
        observed_number="INV-1",
        observed_amount_minor=100,
        candidates=[(first, "INV-1", 100), (second, "INV-2", 100)],
    )
    assert ranked[0].score == Decimal("1.00")
    assert ranked[0].reasons == ("exact_invoice_number", "exact_amount")
    assert choose_unambiguous(ranked) == ranked[0]
    tied = rank_invoice_candidates(
        observed_number=None,
        observed_amount_minor=100,
        candidates=[(first, "INV-1", 100), (second, "INV-2", 100)],
    )
    assert choose_unambiguous(tied) is None


def test_missing_document_blockers_are_reproducible() -> None:
    decision = classify_missing_documents(has_invoice=False, has_acceptance=False)
    assert decision.blockers == (
        BlockerType.MISSING_PAYMENT_DOCUMENT,
        BlockerType.MISSING_ACCEPTANCE_OR_DELIVERY_CONFIRMATION,
    )
    assert decision.next_task == "REQUEST_MISSING_DOCUMENTS"
