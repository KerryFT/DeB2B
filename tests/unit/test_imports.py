import csv
import io

from backend.application.imports import preview_import


def csv_bytes(rows: list[dict[str, object]]) -> bytes:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def test_preview_isolates_invalid_rows() -> None:
    common = {
        "customer_code": "CUS-001",
        "customer_name": "Synthetic Co",
        "tax_id": "SYN-1",
        "issue_date": "2026-08-01",
        "due_date": "2026-08-31",
        "currency": "vnd",
        "account_owner": "owner@example.com",
        "status": "OPEN",
    }
    rows = [
        {**common, "invoice_number": "INV-1", "amount": "100", "outstanding_amount": "100"},
        {**common, "invoice_number": "INV-2", "amount": "100", "outstanding_amount": "101"},
    ]
    preview = preview_import(csv_bytes(rows), "ar.csv")
    assert len(preview.valid) == 1
    assert preview.valid[0].currency == "VND"
    assert preview.invalid[0].row_number == 3
