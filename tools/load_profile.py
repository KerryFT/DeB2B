from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class CapacityReport:
    monthly_cases: int
    average_daily_cases: float
    peak_hour_cases: int
    required_workers_at_30s: int


def model_capacity(monthly_cases: int = 5_000) -> CapacityReport:
    daily = monthly_cases / 30
    peak_hour = round(daily * 0.25)
    required_workers = max(1, round((peak_hour * 30) / 3600 + 0.5))
    return CapacityReport(monthly_cases, round(daily, 2), peak_hour, required_workers)


if __name__ == "__main__":
    print(json.dumps(asdict(model_capacity()), indent=2))
