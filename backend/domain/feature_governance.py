from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class FeatureEvent:
    event_id: str
    occurred_at: datetime
    values: dict[str, int | float | str | bool | None]


@dataclass(frozen=True, slots=True)
class PointInTimeSnapshot:
    entity_type: str
    entity_id: str
    as_of: datetime
    feature_version: str
    features: dict[str, int | float | str | bool | None]
    provenance_event_ids: tuple[str, ...]
    inputs_hash: str


def build_point_in_time_snapshot(
    *,
    entity_type: str,
    entity_id: str,
    as_of: datetime,
    feature_version: str,
    events: list[FeatureEvent],
) -> PointInTimeSnapshot:
    eligible = sorted(
        (event for event in events if event.occurred_at <= as_of),
        key=lambda event: (event.occurred_at, event.event_id),
    )
    features: dict[str, int | float | str | bool | None] = {}
    for event in eligible:
        features.update(event.values)
    canonical: dict[str, Any] = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "as_of": as_of.isoformat(),
        "feature_version": feature_version,
        "features": features,
        "events": [event.event_id for event in eligible],
    }
    inputs_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return PointInTimeSnapshot(
        entity_type,
        entity_id,
        as_of,
        feature_version,
        features,
        tuple(event.event_id for event in eligible),
        inputs_hash,
    )


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    name: str
    version: str
    metric: float
    evaluated_at: datetime
    dataset_version: str


def choose_champion(
    baseline: ModelCandidate,
    challengers: list[ModelCandidate],
    *,
    minimum_improvement: float,
    lower_is_better: bool = True,
) -> ModelCandidate:
    candidates = [baseline, *challengers]
    best = (
        min(candidates, key=lambda item: item.metric)
        if lower_is_better
        else max(candidates, key=lambda item: item.metric)
    )
    improvement = (
        baseline.metric - best.metric if lower_is_better else best.metric - baseline.metric
    )
    return best if improvement >= minimum_improvement else baseline


def model_is_stale(*, evaluated_at: datetime, now: datetime, max_age_days: int) -> bool:
    return (now - evaluated_at).days > max_age_days
