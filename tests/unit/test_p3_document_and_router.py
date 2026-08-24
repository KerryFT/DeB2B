from datetime import date
from decimal import Decimal

import pytest

from backend.application.document_pipeline import ProcessingRoute, choose_page_route
from backend.application.llm_router import RoutePolicy, route_structured
from backend.application.ports import LLMResult
from backend.domain.blocker_engine import classify_case
from backend.domain.blockers import BlockerType
from backend.domain.document_schemas import EvidenceRef, InvoiceExtraction
from backend.infrastructure.fakes import FakeLLMProvider


def test_canonical_invoice_requires_located_evidence() -> None:
    evidence = EvidenceRef(document_id="doc", sheet="AR", cell_range="A2", quote="INV-1")
    extraction = InvoiceExtraction(
        invoice_number="INV-1",
        issue_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31),
        amount=Decimal("120000000"),
        currency="VND",
        evidence={"invoice_number": evidence},
    )
    assert extraction.amount == Decimal("120000000")
    with pytest.raises(ValueError, match="location"):
        EvidenceRef(document_id="doc", quote="unsupported")


def test_page_router_avoids_ocr_for_native_text_and_routes_layout() -> None:
    assert (
        choose_page_route(character_count=500, has_complex_layout=False)
        == ProcessingRoute.NATIVE_TEXT
    )
    assert (
        choose_page_route(character_count=20, has_complex_layout=True)
        == ProcessingRoute.DOCLING_LAYOUT
    )
    assert (
        choose_page_route(character_count=0, has_complex_layout=False, image_quality=0.1)
        == ProcessingRoute.MANUAL_REVIEW
    )


@pytest.mark.asyncio
async def test_router_is_bounded_and_records_fallback_lineage() -> None:
    class BrokenProvider(FakeLLMProvider):
        async def generate_structured(self, **kwargs):  # type: ignore[no-untyped-def]
            return LLMResult("broken", "test", None, None, 1, error_class="schema_invalid")

    routed = await route_structured(
        providers={"broken": BrokenProvider(), "fake": FakeLLMProvider({"invoice": {"ok": True}})},
        policy=RoutePolicy(("broken", "fake"), max_attempts=2),
        task="invoice",
        prompt="untrusted document text",
        schema={"type": "object"},
        model="fixture",
    )
    assert routed.result is not None
    assert routed.result.provider == "fake"
    assert routed.attempts == (("broken", "schema_invalid"), ("fake", None))

    forbidden = await route_structured(
        providers={"fake": FakeLLMProvider()},
        policy=RoutePolicy(("fake",), allow_external=False),
        task="invoice",
        prompt="secret",
        schema={},
        model="fixture",
    )
    assert forbidden.result is None


def test_all_five_blockers_and_complex_case_abstention() -> None:
    decision = classify_case(
        has_invoice=False,
        has_acceptance=False,
        document_data_matches=False,
        customer_disputed=True,
        promise_due=True,
        promise_paid=False,
    )
    assert set(decision.blockers) == {
        BlockerType.MISSING_PAYMENT_DOCUMENT,
        BlockerType.MISSING_ACCEPTANCE_OR_DELIVERY_CONFIRMATION,
        BlockerType.CUSTOMER_DISPUTE,
        BlockerType.BROKEN_PROMISE_TO_PAY,
    }
    assert decision.next_task == "MANUAL_REVIEW"

    incorrect = classify_case(
        has_invoice=True,
        has_acceptance=True,
        document_data_matches=False,
        customer_disputed=False,
        promise_due=False,
        promise_paid=False,
    )
    assert incorrect.blockers == (BlockerType.INCORRECT_DOCUMENT_DATA,)
