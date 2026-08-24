from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from backend.infrastructure.config import get_settings


def test_tenant_rls_is_default_deny_and_cross_tenant_write_is_rejected() -> None:
    engine = create_engine(get_settings().database_url)
    tenant_a, tenant_b = uuid4(), uuid4()
    customer_a, customer_b = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO tenants(id, name, created_at) VALUES (:a,'A',now()),(:b,'B',now())"),
            {"a": tenant_a, "b": tenant_b},
        )
        connection.execute(
            text(
                "INSERT INTO customers(id,tenant_id,code,name,tax_id) "
                "VALUES (:ca,:a,'A-1','A',NULL),(:cb,:b,'B-1','B',NULL)"
            ),
            {"ca": customer_a, "cb": customer_b, "a": tenant_a, "b": tenant_b},
        )
        connection.execute(text("SET LOCAL ROLE ar_app"))
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": str(tenant_a)}
        )
        visible = (
            connection.execute(text("SELECT code FROM customers ORDER BY code")).scalars().all()
        )
        assert visible == ["A-1"]

    with engine.begin() as connection:
        connection.execute(text("SET LOCAL ROLE ar_app"))
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": str(tenant_a)}
        )
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO customers(id,tenant_id,code,name,tax_id) "
                    "VALUES (:id,:other,'X','Cross tenant',NULL)"
                ),
                {"id": uuid4(), "other": tenant_b},
            )


def test_audit_entries_are_append_only_for_application_role() -> None:
    engine = create_engine(get_settings().database_url)
    tenant, entry, aggregate = uuid4(), uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO tenants(id,name,created_at) VALUES (:id,'Audit',now())"),
            {"id": tenant},
        )
        connection.execute(text("SET LOCAL ROLE ar_app"))
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": str(tenant)}
        )
        connection.execute(
            text(
                "INSERT INTO audit_entries(id,tenant_id,occurred_at,actor_type,actor_id,action,"
                "aggregate_type,aggregate_id,correlation_id,payload) VALUES "
                "(:id,:tenant,now(),'USER',NULL,'CREATED','CASE',:aggregate,'test','{}')"
            ),
            {"id": entry, "tenant": tenant, "aggregate": aggregate},
        )

    with engine.begin() as connection:
        connection.execute(text("SET LOCAL ROLE ar_app"))
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": str(tenant)}
        )
        with pytest.raises(DBAPIError):
            connection.execute(
                text("UPDATE audit_entries SET action='TAMPERED' WHERE id=:id"), {"id": entry}
            )
