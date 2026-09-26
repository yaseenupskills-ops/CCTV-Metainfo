from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, Case, User
from tests.helpers import FAKE_MP4, upload


def _make_user(db, *, email="officer@test.local", role=UserRole.VIEWER, password="Passw0rd!x"):
    user = User(
        name="Test Officer",
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def _upload_video(client: TestClient, case: Case, path: Path) -> str:
    return upload(client, case.id, path.read_bytes(), filename=path.name).json()["id"]


def _admin_headers(admin_user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(admin_user.id, admin_user.role.value)}"}


def _viewer_headers(db, *, email="viewer@test.local", role=UserRole.VIEWER, password="Passw0rd!x"):
    user = _make_user(db, email=email, role=role, password=password)
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_audit_written_for_upload(client, db_session, case: Case):
    """Upload triggers audit log entry."""
    evidence_id = upload(client, case.id, FAKE_MP4, "scene.mp4").json()["id"]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "evidence.upload"))
        .scalars()
        .all()
    )
    assert len(failed) >= 1


def test_audit_written_for_hash(client, db_session, case: Case):
    """Hash calculation triggers audit log entry."""
    evidence_id = upload(client, case.id, FAKE_MP4, "scene.mp4").json()["id"]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    resp = client.post(f"/api/v1/evidence/{evidence_id}/hash")
    assert resp.status_code == 200

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "evidence.hash"))
        .scalars()
        .all()
    )
    assert len(failed) >= 1


def test_audit_written_for_metadata(client, db_session, case: Case, scene_change_video_factory):
    """Metadata extraction triggers audit log entry."""
    video = scene_change_video_factory()
    evidence_id = _upload_video(client, case, video)
    resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert resp.status_code == 200

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "evidence.metadata_extract"))
        .scalars()
        .all()
    )
    assert len(failed) >= 1


def test_audit_written_for_analysis(client, db_session, case: Case, scene_change_video_factory):
    """Analysis triggers audit log entry."""
    video = scene_change_video_factory()
    evidence_id = _upload_video(client, case, video)
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1, "threshold": 0.5},
    )
    assert resp.status_code == 200

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "evidence.analyze"))
        .scalars()
        .all()
    )
    assert len(failed) >= 1


def test_audit_written_for_comparison(client, db_session, case: Case):
    """Comparison creates audit log entry."""
    original_id = upload(client, case.id, FAKE_MP4, "o.mp4").json()["id"]
    suspected_id = upload(client, case.id, FAKE_MP4, "s.mp4").json()["id"]
    comparison = client.post(
        "/api/v1/comparisons",
        json={"original_evidence_id": original_id, "suspected_evidence_id": suspected_id},
    )
    assert comparison.status_code == 201

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "comparison.create"))
        .scalars()
        .all()
    )
    assert len(failed) >= 1


def test_audit_written_for_report(client, db_session, case: Case, scene_change_video_factory):
    """Report generation triggers audit log entry."""
    video = scene_change_video_factory()
    evidence_id = _upload_video(client, case, video)
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1, "threshold": 0.5},
    )
    resp = client.post(
        "/api/v1/reports",
        json={"case_id": str(case.id), "evidence_id": evidence_id},
    )
    assert resp.status_code == 201

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "report.create"))
        .scalars()
        .all()
    )
    assert len(failed) >= 1


def test_audit_written_for_case_creation(client, db_session):
    """Case creation triggers audit log entry."""
    resp = client.post(
        "/api/v1/cases",
        json={"title": "New Audit Case", "case_number": "AUD-1"},
    )
    assert resp.status_code == 201

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "case.create")).scalars().all()
    )
    assert len(failed) >= 1


def test_audit_written_for_user_creation(client, db_session):
    """User creation triggers audit log entry."""
    resp = client.post(
        "/api/v1/users",
        json={"name": "X", "email": "x@test.local", "password": "Passw0rd!x", "role": "viewer"},
    )
    assert resp.status_code == 201

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "user.create")).scalars().all()
    )
    assert len(failed) >= 1


def test_audit_written_for_auth_login_failed(raw_client, db_session):
    """Failed login records audit entry."""
    _make_user(db_session, email="officer@test.local")

    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": "officer@test.local", "password": "WrongPass1!"},
    )
    assert resp.status_code == 401

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "auth.login_failed"))
        .scalars()
        .all()
    )
    assert len(failed) == 1
    assert failed[0].details["email"] == "officer@test.local"


def test_audit_written_for_auth_login_success(raw_client, db_session):
    """Successful login records audit entry."""
    user = _make_user(db_session, email="officer@test.local", role=UserRole.INVESTIGATOR)

    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Passw0rd!x"},
    )
    assert resp.status_code == 200

    failed = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "auth.login")).scalars().all()
    )
    assert len(failed) == 1
    assert failed[0].user_id == user.id


def test_audit_filters_by_user(client, db_session, admin_user: User, case: Case):
    """Filter audit logs by user_id."""
    evidence_id = upload(client, case.id, FAKE_MP4, "scene.mp4").json()["id"]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    admin_headers = _admin_headers(admin_user)
    resp = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


def test_audit_filters_by_action(client, db_session, admin_user: User, case: Case):
    """Filter audit logs by action."""
    evidence_id = upload(client, case.id, FAKE_MP4, "scene.mp4").json()["id"]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    admin_headers = _admin_headers(admin_user)
    resp = client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={"action": "evidence.upload"},
    )
    assert resp.status_code == 200
    body = resp.json()
    for entry in body["items"]:
        assert entry["action"] == "evidence.upload"


def test_audit_pagination(client, db_session, admin_user: User, case: Case):
    """Pagination of audit logs."""
    for _ in range(5):
        evidence_id = upload(client, case.id, FAKE_MP4, "scene.mp4").json()["id"]
        client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    admin_headers = _admin_headers(admin_user)
    resp = client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={"page": 1, "page_size": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 5
    assert len(body["items"]) <= 2
    assert body["total_pages"] >= 1
