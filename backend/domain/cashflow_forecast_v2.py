from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean


@dataclass(frozen=True, slots=True)
class CashFlowInput:
    invoice_id: str
    customer_id: str
    account_owner: str
    currency: str
    outstanding_minor: int
    due_date: date
    probabilities: dict[int, float]


@dataclass(frozen=True, slots=True)
class CashFlowComponent:
    invoice_id: str
    currency: str
    contractual_minor: int
    p10_minor: int
    p50_minor: int
    p90_minor: int
    horizon_days: int


@dataclass(frozen=True, slots=True)
class CashFlowBacktest:
    wape: float
    bias: float
    interval_coverage: float


def probabilistic_cashflow(
    inputs: list[CashFlowInput],
    *,
    horizon_days: int,
    downside_factor: float = 0.8,
    upside_factor: float = 1.1,
) -> list[CashFlowComponent]:
    if len({item.invoice_id for item in inputs}) != len(inputs):
        raise ValueError("duplicate invoice would double-count cash flow")
    components: list[CashFlowComponent] = []
    for item in inputs:
        probability = item.probabilities.get(horizon_days)
        if probability is None:
            raise ValueError("probability missing for requested horizon")
        p50 = round(item.outstanding_minor * probability)
        # Quantile-style bounds include both collection timing outcomes for a Bernoulli baseline.
        # Scenario factors only narrow/widen the interval; P50 remains the expected collection.
        p10 = round(p50 * max(0.0, downside_factor - 0.8) * 5)
        p90 = min(
            item.outstanding_minor,
            round(p50 * upside_factor + item.outstanding_minor * (1 - probability)),
        )
        components.append(
            CashFlowComponent(
                item.invoice_id,
                item.currency,
                item.outstanding_minor,
                max(0, min(p50, p10)),
                p50,
                max(p50, p90),
                horizon_days,
            )
        )
    return components


def aggregate_by_currency(components: list[CashFlowComponent]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for item in components:
        row = result.setdefault(item.currency, {"contractual": 0, "p10": 0, "p50": 0, "p90": 0})
        row["contractual"] += item.contractual_minor
        row["p10"] += item.p10_minor
        row["p50"] += item.p50_minor
        row["p90"] += item.p90_minor
    return result


def backtest_cashflow(
    components: list[CashFlowComponent], *, actual_by_invoice: dict[str, int]
) -> CashFlowBacktest:
    if not components:
        raise ValueError("cash-flow backtest requires components")
    actual = [actual_by_invoice.get(item.invoice_id, 0) for item in components]
    total_actual = sum(actual)
    errors = [item.p50_minor - observed for item, observed in zip(components, actual, strict=True)]
    coverage = mean(
        item.p10_minor <= observed <= item.p90_minor
        for item, observed in zip(components, actual, strict=True)
    )
    return CashFlowBacktest(
        sum(abs(error) for error in errors) / total_actual if total_actual else 0.0,
        sum(errors) / total_actual if total_actual else 0.0,
        coverage,
    )
