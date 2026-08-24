from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import zipfile
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import Workbook

DEFAULT_SEED = 20260823
PROFILES = {
    "smoke": {
        "invoices": 10,
        "contracts": 5,
        "po_acceptance": 10,
        "threads": 10,
        "disputes": 5,
        "promises": 5,
        "bank": 10,
    },
    "full": {
        "invoices": 100,
        "contracts": 50,
        "po_acceptance": 100,
        "threads": 100,
        "disputes": 50,
        "promises": 50,
        "bank": 50,
    },
}
COMPANIES = ["Sao Mai", "An Bình", "Minh Hà", "Việt Phúc", "Đông Dương", "Thiên Lam"]
BLOCKERS = [
    "MISSING_PAYMENT_DOCUMENT",
    "INCORRECT_DOCUMENT_DATA",
    "MISSING_ACCEPTANCE_OR_DELIVERY_CONFIRMATION",
    "CUSTOMER_DISPUTE",
    "BROKEN_PROMISE_TO_PAY",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def invoice_rows(count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)  # noqa: S311 - deterministic synthetic fixtures, not security
    start = date(2026, 7, 1)
    rows = []
    for index in range(1, count + 1):
        issue = start + timedelta(days=index % 28)
        amount = rng.randrange(10, 250) * 1_000_000
        blocker = BLOCKERS[(index - 1) % len(BLOCKERS)]
        rows.append(
            {
                "invoice_number": f"INV-2026-{index:04d}",
                "customer_code": f"CUS-{(index - 1) % len(COMPANIES) + 1:03d}",
                "customer_name": f"Công ty {COMPANIES[(index - 1) % len(COMPANIES)]} (synthetic)",
                "tax_id": f"SYN-{index:010d}",
                "issue_date": issue.isoformat(),
                "due_date": (issue + timedelta(days=30)).isoformat(),
                "amount": amount,
                "currency": "VND",
                "outstanding_amount": amount,
                "account_owner": "demo-owner@example.com",
                "status": "OPEN",
                "gold_blocker": blocker,
                "has_invoice": blocker != "MISSING_PAYMENT_DOCUMENT",
                "has_acceptance": blocker != "MISSING_ACCEPTANCE_OR_DELIVERY_CONFIRMATION",
                "document_data_matches": blocker != "INCORRECT_DOCUMENT_DATA",
                "customer_disputed": blocker == "CUSTOMER_DISPUTE",
                "promise_due": blocker == "BROKEN_PROMISE_TO_PAY",
                "promise_paid": False,
            }
        )
    return rows


def write_tabular(root: Path, rows: list[dict[str, Any]]) -> list[Path]:
    csv_path = root / "invoices.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    xlsx_path = root / "invoices.xlsx"
    workbook = Workbook()
    workbook.properties.created = datetime(1980, 1, 1)
    workbook.properties.modified = datetime(1980, 1, 1)
    workbook.properties.creator = "AR Operations synthetic generator"
    sheet = workbook.active
    sheet.title = "AR"
    sheet.append(list(rows[0]))
    for row in rows:
        sheet.append(list(row.values()))
    buffer = BytesIO()
    workbook.save(buffer)
    source = zipfile.ZipFile(BytesIO(buffer.getvalue()))
    with zipfile.ZipFile(xlsx_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            target.writestr(info, source.read(name))
    source.close()
    return [csv_path, xlsx_path]


def write_bank_csv(root: Path, rows: list[dict[str, Any]], count: int) -> Path:
    path = root / "bank.csv"
    fields = ["external_id", "booked_date", "amount", "currency", "reference"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(count):
            invoice = rows[index % len(rows)]
            writer.writerow(
                {
                    "external_id": f"BANK-SYN-{index + 1:04d}",
                    "booked_date": invoice["due_date"],
                    "amount": invoice["outstanding_amount"],
                    "currency": invoice["currency"],
                    "reference": f"THANH TOAN {invoice['invoice_number']}",
                }
            )
    return path


def generate(profile: str, output: Path, seed: int = DEFAULT_SEED) -> Path:
    counts = PROFILES[profile]
    root = output / f"{profile}-v1"
    root.mkdir(parents=True, exist_ok=True)
    rows = invoice_rows(counts["invoices"], seed)
    artifacts = write_tabular(root, rows)
    artifacts.append(write_bank_csv(root, rows, counts["bank"]))
    case_path = root / "cases.jsonl"
    case_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    artifacts.append(case_path)
    manifest = {
        "dataset_version": "synthetic-v1",
        "profile": profile,
        "seed": seed,
        "source": "synthetic",
        "license": "project-generated",
        "counts": counts,
        "splits": {"train": 70, "validation": 15, "test": 15}
        if profile == "full"
        else {"ci": counts["invoices"]},
        "generator_version": "1.0.0",
        "gold_review": "synthetic-rules-reviewed-v1",
        "artifacts": [
            {"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in artifacts
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(manifest_path)
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(PROFILES), default="smoke")
    parser.add_argument("--output", type=Path, default=Path("data/generated"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    generate(args.profile, args.output, args.seed)


if __name__ == "__main__":
    main()
