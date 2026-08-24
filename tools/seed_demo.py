from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from backend.application.imports import preview_import
from backend.application.invoice_import_service import upsert_invoice_rows
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import Tenant

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USER_ID = "00000000-0000-0000-0000-000000000002"


def main() -> None:
    fixture = Path("data/fixtures/smoke-v1/invoices.xlsx")
    preview = preview_import(fixture.read_bytes(), fixture.name)
    if preview.invalid:
        raise SystemExit(f"fixture contains {len(preview.invalid)} invalid rows")
    with SessionFactory.begin() as session:
        tenant = session.scalar(select(Tenant).where(Tenant.id == TENANT_ID))
        if tenant is None:
            session.add(Tenant(id=TENANT_ID, name="AR Operations Demo"))
            session.flush()
        result = upsert_invoice_rows(
            session,
            tenant_id=TENANT_ID,
            rows=preview.valid,
            correlation_id="demo-seed-v1",
            actor_id=USER_ID,
        )
    print(result)


if __name__ == "__main__":
    main()
