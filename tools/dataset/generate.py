from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
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
            content = source.read(name)
            if name == "docProps/core.xml":
                content = re.sub(
                    rb"<dcterms:modified[^>]*>.*?</dcterms:modified>",
                    (
                        b'<dcterms:modified xsi:type="dcterms:W3CDTF">'
                        b"1980-01-01T00:00:00Z</dcterms:modified>"
                    ),
                    content,
                )
            target.writestr(info, content)
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


def write_v1_scenarios(root: Path, rows: list[dict[str, Any]]) -> Path:
    path = root / "v1-scenarios.json"
    invoice = rows[0]
    scenarios = {
        "misa": {
            "pages": 2,
            "checkpoint": "misa-checkpoint-2",
            "events": ["token_expired", "throttled", "duplicate", "partial_failure"],
        },
        "outlook": {
            "conversation_id": "conversation-synthetic-1",
            "delta_tokens": ["delta-1", "delta-2"],
            "events": ["duplicate_webhook", "missed", "subscription_expired"],
            "attachments": ["acceptance-synthetic.pdf"],
        },
        "zalo": {
            "template": {"id": "payment-reminder", "version": 1, "locale": "vi-VN"},
            "recipients": ["verified", "unverified", "suppressed"],
            "outcomes": ["success", "reject", "timeout", "duplicate", "policy_block"],
        },
        "bank": [
            {"kind": "partial", "invoice": invoice["invoice_number"], "amount": 1_000_000},
            {"kind": "split", "invoices": [rows[0]["invoice_number"], rows[1]["invoice_number"]]},
            {"kind": "aggregate", "transactions": ["BANK-A", "BANK-B"]},
            {"kind": "fee", "fee_minor": 5_000},
            {"kind": "reversal", "reversal_of": "BANK-SYN-0001"},
            {"kind": "fx_without_rate", "currency": "USD", "disposition": "manual_review"},
            {"kind": "ambiguous", "candidates": 2},
        ],
        "payment_rules": [
            {"customer": "CUS-001", "version": 2, "grace_days": 3},
            {"customer": "CUS-002", "version": 1, "grace_days": 7},
            {"customer": "CUS-003", "version": 2, "conflict": True},
        ],
        "rbac": {
            "tenants": ["tenant-a", "tenant-b"],
            "roles": [
                "tenant_admin",
                "ar_manager",
                "ar_specialist",
                "account_owner",
                "approver",
                "auditor",
            ],
        },
        "llm": {
            "providers": ["openai", "gemini", "anthropic"],
            "usage_cases": ["primary", "fallback", "missing_usage", "unknown_pricing"],
            "pricing_versions": 2,
        },
        "forecast": {
            "as_of": "2026-08-24",
            "history_months": 12,
            "broken_promises": 2,
            "partial_payments": 3,
        },
    }
    path.write_text(json.dumps(scenarios, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_v2_scenarios(root: Path, rows: list[dict[str, Any]]) -> Path:
    path = root / "v2-scenarios.json"
    scenarios = {
        "tenants": ["tenant-a", "tenant-b"],
        "automation": [
            {"case": "safe-shadow", "expected": "SHADOW_ELIGIBLE", "send": False},
            {"case": "paid-before-send", "expected": "BLOCKED"},
            {"case": "disputed-before-send", "expected": "BLOCKED"},
            {"case": "recipient-changed", "expected": "BLOCKED"},
            {"case": "duplicate-timer", "expected": "IDEMPOTENT"},
            {"case": "suppressed", "expected": "BLOCKED"},
            {"case": "bounce-circuit", "expected": "BLOCKED"},
            {"case": "kill-switch-race", "expected": "BLOCKED"},
        ],
        "escalation": [
            {"case": "disputed", "allowed": "temporary_pause", "human_decision": True},
            {"case": "missing-data", "allowed": "manager_review", "human_decision": True},
            {"case": "prompt-injection", "forbidden": "threat_or_public_shaming"},
        ],
        "disputes": [
            {"labels": ["pricing_amount_mismatch", "po_mismatch"], "evidence": ["span-1"]},
            {"labels": ["unknown"], "evidence": []},
            {"lifecycle": ["detected", "human_corrected", "resolved", "reopened"]},
        ],
        "time_series": {
            "as_of": "2026-08-24",
            "horizons": [7, 14, 30],
            "conditions": ["censored", "partial", "seasonality", "drift", "late_arrival"],
            "invoice_ids": [row["invoice_number"] for row in rows],
        },
        "behavior_profiles": [
            "new_sparse",
            "consistent",
            "variable",
            "dispute_heavy",
            "promise_broken",
        ],
        "benchmark": {
            "managers": ["manager-a", "manager-b", "manager-small-cohort"],
            "portfolio_mix": ["current", "aged", "disputed"],
            "reassignment": True,
            "minimum_cohort_suppression": True,
        },
    }
    path.write_text(json.dumps(scenarios, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate(profile: str, output: Path, seed: int = DEFAULT_SEED) -> Path:
    counts = PROFILES[profile]
    root = output / f"{profile}-v2"
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
    artifacts.append(write_v1_scenarios(root, rows))
    artifacts.append(write_v2_scenarios(root, rows))
    manifest = {
        "dataset_version": "synthetic-v3",
        "profile": profile,
        "seed": seed,
        "source": "synthetic",
        "license": "project-generated",
        "counts": counts,
        "splits": {"train": 70, "validation": 15, "test": 15}
        if profile == "full"
        else {"ci": counts["invoices"]},
        "generator_version": "3.0.0",
        "gold_review": "synthetic-rules-reviewed-v2",
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
