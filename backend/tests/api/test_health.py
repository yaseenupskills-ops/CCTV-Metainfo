from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_root_returns_app_info(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert "name" in body
    assert body["health"] == "/api/v1/health"
