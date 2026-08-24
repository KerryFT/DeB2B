from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from backend.domain.blocker_engine import classify_case


def macro_f1(rows: list[dict[str, Any]]) -> float:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    labels = {str(row["gold_blocker"]) for row in rows}
    for row in rows:
        decision = classify_case(
            has_invoice=bool(row["has_invoice"]),
            has_acceptance=bool(row["has_acceptance"]),
            document_data_matches=bool(row["document_data_matches"]),
            customer_disputed=bool(row["customer_disputed"]),
            promise_due=bool(row["promise_due"]),
            promise_paid=bool(row["promise_paid"]),
        )
        predicted = decision.blockers[0].value if len(decision.blockers) == 1 else "MANUAL_REVIEW"
        gold = str(row["gold_blocker"])
        for label in labels:
            if predicted == label and gold == label:
                counts[label]["tp"] += 1
            elif predicted == label:
                counts[label]["fp"] += 1
            elif gold == label:
                counts[label]["fn"] += 1
    scores = []
    for label in sorted(labels):
        tp, fp, fn = counts[label]["tp"], counts[label]["fp"], counts[label]["fn"]
        denominator = 2 * tp + fp + fn
        scores.append(2 * tp / denominator if denominator else 1.0)
    return sum(scores) / len(scores)


def evaluate(path: Path) -> dict[str, float | int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    held_out = [row for index, row in enumerate(rows) if index % 5 == 0]
    return {"macro_f1": macro_f1(held_out), "held_out_count": len(held_out)}
