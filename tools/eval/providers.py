from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def regression_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    providers = sorted({str(row["provider"]) for row in results})
    matrix = {}
    for provider in providers:
        rows = [row for row in results if row["provider"] == provider]
        matrix[provider] = {
            "schema_success_rate": sum(bool(row["schema_valid"]) for row in rows) / len(rows),
            "mean_latency_ms": mean(float(row["latency_ms"]) for row in rows),
            "estimated_cost_usd": sum(float(row.get("cost_usd", 0)) for row in rows),
        }
    eligible = [name for name, values in matrix.items() if values["schema_success_rate"] >= 0.95]
    selected = min(eligible, key=lambda name: matrix[name]["mean_latency_ms"]) if eligible else None
    return {"providers": matrix, "selected_route": selected, "sample_count": len(results)}


def write_report(results_path: Path, output_path: Path) -> None:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    output_path.write_text(json.dumps(regression_report(results), indent=2), encoding="utf-8")
