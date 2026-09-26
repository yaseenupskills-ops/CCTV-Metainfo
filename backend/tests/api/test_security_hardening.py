"""Security hardening tests: rate limiting, request size, CORS, path leaks."""

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.models import Case
from tests.helpers import FAKE_MP4, upload


def test_login_rate_limited_after_five_attempts(raw_client: TestClient):
    payload = {"email": "nobody@test.local", "password": "wrong-password"}
    for _ in range(5):
        assert raw_client.post("/api/v1/auth/login", json=payload).status_code == 401

    blocked = raw_client.post("/api/v1/auth/login", json=payload)
    assert blocked.status_code == 429
    assert "Too many login attempts" in blocked.json()["detail"]


def test_rate_limit_does_not_apply_after_reset(raw_client: TestClient):
    payload = {"email": "nobody@test.local", "password": "wrong-password"}
    for _ in range(5):
        raw_client.post("/api/v1/auth/login", json=payload)
    from app.core.rate_limit import reset_rate_limits

    reset_rate_limits()
    assert raw_client.post("/api/v1/auth/login", json=payload).status_code == 401


def test_rate_limit_exception_maps_to_429():
    error = RateLimitError()
    assert error.status_code == 429


def test_request_body_over_limit_rejected(client: TestClient, case: Case):
    oversized = {"title": "x" * (settings.max_request_body_size + 10_000)}
    resp = client.post("/api/v1/cases", json=oversized)
    assert resp.status_code == 413


def test_multipart_upload_exempt_from_json_body_limit(
    client: TestClient, case: Case, monkeypatch
):
    monkeypatch.setattr(settings, "max_request_body_size", 10)
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 201


def test_cors_allows_configured_origin(client: TestClient):
    resp = client.options(
        "/api/v1/evidence",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client: TestClient):
    resp = client.options(
        "/api/v1/evidence",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") is None


def test_cors_does_not_allow_every_method(client: TestClient):
    resp = client.options(
        "/api/v1/evidence",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    allowed = resp.headers.get("access-control-allow-methods", "")
    assert "GET" in allowed
    assert allowed.strip("*") == allowed  # no wildcard


def test_no_internal_storage_paths_in_responses(
    client: TestClient, case: Case, sample_video: Path
):
    evidence_id = upload(client, case.id, sample_video.read_bytes(), filename="clip.mp4").json()[
        "id"
    ]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    forbidden = [
        str(settings.storage_originals_dir),
        str(settings.storage_processed_dir),
        str(settings.storage_reports_dir),
        "C:\\",
        "storage/evidence",
    ]

    for path in [
        "/api/v1/evidence?page=1&page_size=100",
        f"/api/v1/evidence/{evidence_id}",
        f"/api/v1/evidence/{evidence_id}/analysis",
        f"/api/v1/evidence/{evidence_id}/anomaly-score",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200
        text = resp.text
        for token in forbidden:
            assert token not in text, f"{token!r} leaked in {path}"


def test_strict_case_schema_rejects_extra_fields(client: TestClient, case: Case):
    resp = client.post(
        "/api/v1/cases",
        json={"title": "Strict", "description": "x", "unexpected_field": "nope"},
    )
    assert resp.status_code == 422


def test_strict_login_schema_rejects_extra_fields(raw_client: TestClient):
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.c", "password": "password", "remember_me": True},
    )
    assert resp.status_code == 422


def test_sql_injection_attempt_is_safe(client: TestClient, case: Case):
    upload(client, case.id, FAKE_MP4, filename="clip.mp4")
    payload = "'; DROP TABLE evidence; --"
    resp = client.get(
        "/api/v1/evidence", params={"page": 1, "page_size": 100, "search": payload}
    )
    assert resp.status_code == 200

    # Evidence table still exists and no rows were lost.
    resp = client.get("/api/v1/evidence", params={"page": 1, "page_size": 100})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_invalid_uuid_returns_422_not_500(client: TestClient):
    resp = client.get("/api/v1/evidence/not-a-uuid")
    assert resp.status_code == 422


def test_unknown_uuid_returns_404(client: TestClient):
    resp = client.get(f"/api/v1/evidence/{uuid.uuid4()}")
    assert resp.status_code == 404
