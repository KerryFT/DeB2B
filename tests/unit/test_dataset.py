import json
from pathlib import Path

from tools.dataset.generate import generate


def test_seeded_dataset_is_reproducible(tmp_path: Path) -> None:
    first = generate("smoke", tmp_path / "one")
    second = generate("smoke", tmp_path / "two")
    left = json.loads(first.read_text(encoding="utf-8"))
    right = json.loads(second.read_text(encoding="utf-8"))
    assert left["counts"] == right["counts"]
    assert left["artifacts"] == right["artifacts"]
    assert left["source"] == "synthetic"
