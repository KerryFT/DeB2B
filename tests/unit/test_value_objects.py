from datetime import date
from decimal import Decimal

import pytest

from backend.domain.value_objects import DateRange, Money, idempotency_key


def test_money_is_exact_and_currency_checked() -> None:
    amount = Money.from_decimal(Decimal("120000000"), "vnd")
    assert amount.minor_units == 120_000_000
    assert amount.currency == "VND"
    with pytest.raises(ValueError, match="currency mismatch"):
        _ = amount + Money(1, "USD")


def test_date_range_and_idempotency_invariants() -> None:
    with pytest.raises(ValueError):
        DateRange(date(2026, 8, 2), date(2026, 8, 1))
    assert idempotency_key("tenant", "case", "draft") == "tenant:case:draft"
