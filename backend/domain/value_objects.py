from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantId:
    value: UUID


@dataclass(frozen=True, slots=True)
class Money:
    minor_units: int
    currency: str = "VND"

    def __post_init__(self) -> None:
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("currency must be a three-letter ISO code")
        object.__setattr__(self, "currency", self.currency.upper())

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str = "VND", scale: int = 0) -> Money:
        multiplier = Decimal(10) ** scale
        minor = int((amount * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(minor, currency)

    def __add__(self, other: Money) -> Money:
        self._same_currency(other)
        return Money(self.minor_units + other.minor_units, self.currency)

    def _same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError("currency mismatch")


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("date range end precedes start")


def idempotency_key(*parts: object) -> str:
    normalized = [str(part).strip() for part in parts]
    if not all(normalized):
        raise ValueError("idempotency key parts cannot be empty")
    return ":".join(normalized)
