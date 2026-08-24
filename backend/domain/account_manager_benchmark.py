from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True, slots=True)
class ManagerCaseOutcome:
    case_id: str
    manager_id: str
    follow_up_hours: float
    document_completion_days: float
    dispute_resolution_days: float | None
    approval_turnaround_hours: float
    collected_ratio: float
    portfolio_difficulty: float
    inherited: bool = False
    attribution_share: float = 1.0


@dataclass(frozen=True, slots=True)
class ManagerBenchmark:
    manager_id: str
    sample_size: int
    raw_timeliness: float | None
    adjusted_timeliness: float | None
    raw_collection_outcome: float | None
    adjusted_collection_outcome: float | None
    uncertainty: float | None
    suppressed: bool
    warnings: tuple[str, ...]
    case_ids: tuple[str, ...]


def benchmark_managers(
    outcomes: list[ManagerCaseOutcome], *, minimum_sample: int = 3
) -> list[ManagerBenchmark]:
    grouped: dict[str, list[ManagerCaseOutcome]] = {}
    for item in outcomes:
        if not 0 < item.attribution_share <= 1:
            raise ValueError("attribution share must be within (0, 1]")
        grouped.setdefault(item.manager_id, []).append(item)
    rows: list[ManagerBenchmark] = []
    for manager_id, items in sorted(grouped.items()):
        if len(items) < minimum_sample:
            rows.append(
                ManagerBenchmark(
                    manager_id,
                    len(items),
                    None,
                    None,
                    None,
                    None,
                    None,
                    True,
                    ("minimum_cohort_not_met",),
                    (),
                )
            )
            continue
        raw_time = mean(item.follow_up_hours for item in items)
        raw_outcome = sum(item.collected_ratio * item.attribution_share for item in items) / sum(
            item.attribution_share for item in items
        )
        adjusted_times = [
            item.follow_up_hours / max(0.25, item.portfolio_difficulty) for item in items
        ]
        adjusted_outcomes = [
            item.collected_ratio * max(0.25, item.portfolio_difficulty) for item in items
        ]
        center = mean(adjusted_outcomes)
        uncertainty = mean(abs(value - center) for value in adjusted_outcomes)
        warnings: list[str] = []
        if any(item.inherited for item in items):
            warnings.append("includes_inherited_cases")
        if max(item.portfolio_difficulty for item in items) > 2 * min(
            item.portfolio_difficulty for item in items
        ):
            warnings.append("heterogeneous_portfolio")
        rows.append(
            ManagerBenchmark(
                manager_id,
                len(items),
                raw_time,
                mean(adjusted_times),
                raw_outcome,
                mean(adjusted_outcomes),
                uncertainty,
                False,
                tuple(warnings),
                tuple(item.case_id for item in items),
            )
        )
    return rows
