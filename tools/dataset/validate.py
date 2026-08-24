from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def validate_dataset(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    errors = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if not path.is_file():
            errors.append(f"missing {path.name}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != artifact["sha256"]:
            errors.append(f"checksum mismatch {path.name}")
    if manifest["profile"] == "full" and sum(manifest["splits"].values()) != 100:
        errors.append("full split counts must total 100")
    if manifest["source"] != "synthetic" or not manifest.get("license"):
        errors.append("dataset provenance is incomplete")
    return {"valid": not errors, "errors": errors, "artifact_count": len(manifest["artifacts"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    report = validate_dataset(args.manifest)
    print(json.dumps(report, ensure_ascii=False))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
