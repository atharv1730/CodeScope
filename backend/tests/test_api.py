"""API tests that don't require a live database.

These cover request validation and the health endpoint's shape. Full
pipeline/endpoint tests that read/write analyses need a Postgres instance and
are run via docker-compose, not here.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_rejects_non_github_url():
    # Validation happens before any DB access, so this is safe without a DB.
    resp = client.post("/analyze", json={"repo_url": "https://gitlab.com/a/b"})
    assert resp.status_code == 422
    assert "GitHub" in resp.json()["detail"]


def test_analyze_rejects_empty_url():
    resp = client.post("/analyze", json={"repo_url": "   "})
    assert resp.status_code == 422


def test_root_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "service" in resp.json()


def test_health_shape():
    # Returns 200 even when DB/Redis are down (status just reports "degraded").
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert set(["status", "database", "redis"]).issubset(body.keys())
