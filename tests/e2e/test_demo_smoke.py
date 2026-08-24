from fastapi.testclient import TestClient

from services.api.main import app

HEADERS = {
    "x-dev-user-id": "00000000-0000-0000-0000-000000000002",
    "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001",
    "x-dev-role": "approver",
}


def test_demo_health_dashboard_and_case_queue() -> None:
    with TestClient(app) as client:
        assert client.get("/live").json() == {"status": "ok"}
        assert client.get("/ready").json() == {"status": "ok"}
        dashboard = client.get("/api/v1/dashboard", headers=HEADERS)
        assert dashboard.status_code == 200
        assert dashboard.json()["open_cases"] == 10
        assert dashboard.json()["outstanding_minor"] > 0
        cases = client.get("/api/v1/cases", headers=HEADERS)
        assert cases.status_code == 200
        assert len(cases.json()) == 10
