"""
Milestone 1 tests: the app boots, connects to Mongo via its lifespan handler,
and the health/root endpoints respond sensibly whether or not the database
happens to be reachable.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert body["docs"] == "/docs"


def test_health_check_reports_status_and_database():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    # We don't assert "ok" specifically - a dev machine without Mongo running
    # should still get a 200 with status "degraded", not a crash.
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"connected", "unavailable"}
    assert body["environment"] == "development"


def test_health_check_is_under_api_prefix():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 404
