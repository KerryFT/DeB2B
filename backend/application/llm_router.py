from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.application.ports import LLMProvider, LLMResult


@dataclass(frozen=True, slots=True)
class RoutePolicy:
    providers: tuple[str, ...]
    max_attempts: int = 2
    allow_external: bool = True


@dataclass(frozen=True, slots=True)
class RoutedResult:
    result: LLMResult | None
    attempts: tuple[tuple[str, str | None], ...]


async def route_structured(
    *,
    providers: dict[str, LLMProvider],
    policy: RoutePolicy,
    task: str,
    prompt: str,
    schema: dict[str, Any],
    model: str,
) -> RoutedResult:
    if not policy.allow_external:
        return RoutedResult(None, (("router", "external_processing_forbidden"),))
    attempts: list[tuple[str, str | None]] = []
    for name in policy.providers[: policy.max_attempts]:
        provider = providers.get(name)
        if provider is None:
            attempts.append((name, "provider_unavailable"))
            continue
        try:
            result = await provider.generate_structured(
                task=task, prompt=prompt, schema=schema, model=model
            )
        except Exception as exc:  # providers are an explicit failure boundary
            attempts.append((name, type(exc).__name__))
            continue
        attempts.append((name, result.error_class))
        if result.schema_valid and result.data is not None:
            return RoutedResult(result, tuple(attempts))
    return RoutedResult(None, tuple(attempts))
