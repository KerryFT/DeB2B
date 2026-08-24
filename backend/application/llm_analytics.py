from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from statistics import quantiles


@dataclass(frozen=True, slots=True)
class PricingVersion:
    provider: str
    model: str
    effective_from: datetime
    currency: str
    input_per_million: Decimal
    output_per_million: Decimal
    version: int


@dataclass(frozen=True, slots=True)
class LLMEvent:
    provider: str
    model: str
    task_type: str
    prompt_version: str
    route: str
    occurred_at: datetime
    latency_ms: int
    success: bool
    schema_valid: bool
    fallback: bool
    input_tokens: int | None
    output_tokens: int | None


def estimate_cost(
    event: LLMEvent, pricing: list[PricingVersion]
) -> tuple[Decimal | None, str | None]:
    versions = [
        item
        for item in pricing
        if item.provider == event.provider
        and item.model == event.model
        and item.effective_from <= event.occurred_at
    ]
    if not versions or event.input_tokens is None or event.output_tokens is None:
        return None, None
    selected = max(versions, key=lambda item: (item.effective_from, item.version))
    cost = (
        Decimal(event.input_tokens) * selected.input_per_million
        + Decimal(event.output_tokens) * selected.output_per_million
    ) / Decimal(1_000_000)
    return cost, selected.currency


def aggregate_online(
    events: list[LLMEvent], pricing: list[PricingVersion]
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[LLMEvent]] = {}
    for event in events:
        groups.setdefault((event.provider, event.model, event.task_type), []).append(event)
    rows: list[dict[str, object]] = []
    for (provider, model, task), items in sorted(groups.items()):
        latencies = sorted(item.latency_ms for item in items)
        p95 = quantiles(latencies, n=20, method="inclusive")[18] if len(items) > 1 else latencies[0]
        costs = [estimate_cost(item, pricing)[0] for item in items]
        known_costs = [cost for cost in costs if cost is not None]
        rows.append(
            {
                "provider": provider,
                "model": model,
                "task_type": task,
                "requests": len(items),
                "success_rate": sum(item.success for item in items) / len(items),
                "schema_validity_rate": sum(item.schema_valid for item in items) / len(items),
                "fallback_rate": sum(item.fallback for item in items) / len(items),
                "latency_p50_ms": latencies[(len(latencies) - 1) // 2],
                "latency_p95_ms": round(p95),
                "estimated_cost": sum(known_costs, Decimal("0")) if known_costs else None,
                "unknown_pricing_requests": sum(cost is None for cost in costs),
                "metric_kind": "online_operational",
            }
        )
    return rows
