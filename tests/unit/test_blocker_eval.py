import json
from pathlib import Path

from tools.dataset.generate import generate
from tools.eval.blockers import evaluate


def test_held_out_blocker_macro_f1_is_reported(tmp_path: Path) -> None:
    manifest = generate("full", tmp_path)
    report = evaluate(manifest.parent / "cases.jsonl")
    assert report["held_out_count"] == 20
    assert report["macro_f1"] >= 0.85
    (tmp_path / "blocker-report.json").write_text(json.dumps(report), encoding="utf-8")
