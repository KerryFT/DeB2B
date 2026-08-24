from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.infrastructure.config import get_settings
from services.api.main import app


def test_all_v2_derived_tables_force_tenant_rls() -> None:
    tables = {
        "feature_definitions",
        "feature_snapshots",
        "model_registry",
        "prediction_runs",
        "prediction_records",
        "automation_policies",
        "automation_decisions",
        "dispute_root_causes",
        "escalation_recommendations",
        "customer_behavior_snapshots",
        "account_manager_benchmarks",
        "derived_job_runs",
    }
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, count(p.policyname) "
                "FROM pg_class c LEFT JOIN pg_policies p ON p.tablename=c.relname "
                "WHERE c.relname = ANY(:tables) "
                "GROUP BY c.relname,c.relrowsecurity,c.relforcerowsecurity"
            ),
            {"tables": list(tables)},
        ).all()
    assert {row[0] for row in rows} == tables
    assert all(row[1] and row[2] and row[3] >= 1 for row in rows)


def test_v2_demo_api_reconciles_and_defaults_automation_safe() -> None:
    tenant, customer, case = uuid4(), uuid4(), uuid4()
    engine = create_engine(get_settings().database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO tenants(id,name,created_at) VALUES (:id,'V2 API test',now())"),
            {"id": tenant},
        )
        connection.execute(
            text(
                "INSERT INTO customers(id,tenant_id,code,name,tax_id) "
                "VALUES (:id,:tenant,'V2-C','Synthetic V2',NULL)"
            ),
            {"id": customer, "tenant": tenant},
        )
        connection.execute(
            text(
                "INSERT INTO payment_cases(id,tenant_id,status,version,next_action_at) "
                "VALUES (:id,:tenant,'IMPORTED',1,NULL)"
            ),
            {"id": case, "tenant": tenant},
        )
        for index in range(3):
            invoice = uuid4()
            connection.execute(
                text(
                    "INSERT INTO invoices(id,tenant_id,customer_id,invoice_number,issue_date,"
                    "due_date,amount_minor,outstanding_minor,currency,source_fingerprint,"
                    "account_owner) "
                    "VALUES (:id,:tenant,:customer,:number,:issue,:due,1000,700,'VND',:fingerprint,"
                    "'manager@test')"
                ),
                {
                    "id": invoice,
                    "tenant": tenant,
                    "customer": customer,
                    "number": f"V2-{index}",
                    "issue": date(2026, 7, 1),
                    "due": date(2026, 8, 1),
                    "fingerprint": f"v2-{uuid4().hex}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO case_invoices(id,tenant_id,case_id,invoice_id) "
                    "VALUES (:id,:tenant,:case,:invoice)"
                ),
                {"id": uuid4(), "tenant": tenant, "case": case, "invoice": invoice},
            )
    headers = {
        "x-dev-user-id": str(uuid4()),
        "x-dev-tenant-id": str(tenant),
        "x-dev-role": "tenant_admin",
    }
    client = TestClient(app)
    probability = client.get("/api/v2/probability-to-pay", headers=headers)
    assert probability.status_code == 200
    assert len(probability.json()["predictions"]) == 3
    forecast = client.get("/api/v2/cash-flow?horizon_days=30", headers=headers)
    assert forecast.status_code == 200
    reconciliation = forecast.json()["reconciliation"]
    assert reconciliation["difference_minor"] == 0
    policy = client.get("/api/v2/automation/policy", headers=headers)
    assert policy.status_code == 200
    assert policy.json()["mode"] == "disabled"
    assert policy.json()["kill_switch"] is True
    assert policy.json()["external_delivery_enabled"] is False
    evaluation = client.post(f"/api/v2/automation/evaluate/{case}", headers=headers)
    assert evaluation.status_code == 200
    assert evaluation.json()["disposition"] == "BLOCKED"
    assert evaluation.json()["external_delivery_attempted"] is False
    no_confirmation = client.post(
        "/api/v2/automation/policy",
        headers=headers,
        json={"mode": "canary", "kill_switch": False, "canary_percent": 1},
    )
    assert no_confirmation.status_code == 409
    escalation = client.post(f"/api/v2/escalation/{case}/generate", headers=headers)
    assert escalation.status_code == 200
    recommendation_id = escalation.json()["recommendations"][0]["id"]
    feedback = client.post(
        f"/api/v2/escalation/recommendations/{recommendation_id}/feedback",
        headers=headers,
        json={"decision": "accepted"},
    )
    assert feedback.status_code == 200
    benchmark = client.get("/api/v2/account-manager-benchmark", headers=headers)
    assert benchmark.status_code == 200
    assert benchmark.json()["benchmarks"][0]["suppressed"] is False
