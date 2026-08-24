from pathlib import Path

from tools.dataset.generate import generate
from tools.dataset.validate import validate_dataset
from tools.eval.providers import regression_report


def test_full_dataset_manifest_checksums_splits_and_provenance(tmp_path: Path) -> None:
    manifest = generate("full", tmp_path)
    report = validate_dataset(manifest)
    assert report["valid"]
    assert report["artifact_count"] == 4


def test_cross_provider_regression_records_route_decision() -> None:
    report = regression_report(
        [
            {"provider": "openai", "schema_valid": True, "latency_ms": 20, "cost_usd": 0.01},
            {"provider": "gemini", "schema_valid": True, "latency_ms": 10, "cost_usd": 0.02},
            {"provider": "anthropic", "schema_valid": False, "latency_ms": 5, "cost_usd": 0.03},
        ]
    )
    assert report["selected_route"] == "gemini"
    assert report["sample_count"] == 3
