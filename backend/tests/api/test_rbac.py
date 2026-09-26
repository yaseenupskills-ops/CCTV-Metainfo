import pytest
from sqlalchemy import select

from app.core.enums import CaseStatus, UserRole
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, Case, User
from tests.helpers import FAKE_MP4

PASSWORD = "Passw0rd!x"


def _make_user(db, *, email, role):
    user = User(
        name=email,
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def _headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


@pytest.fixture()
def staff(db_session):
    inv = _make_user(db_session, email="inv@rbac.local", role=UserRole.INVESTIGATOR)
    viewer = _make_user(db_session, email="viewer@rbac.local", role=UserRole.VIEWER)
    admin = _make_user(db_session, email="admin@rbac.local", role=UserRole.ADMIN)
    case = Case(
        case_number="CASE-RBAC",
        title="RBAC Case",
        status=CaseStatus.OPEN,
        investigator_id=inv.id,
    )
    db_session.add(case)
    db_session.commit()
    return inv, viewer, admin, case


def test_protected_endpoints_require_token(raw_client):
    for path in (
        "/api/v1/evidence",
        "/api/v1/evidence/00000000-0000-0000-0000-000000000001",
        "/api/v1/dashboard/stats",
        "/api/v1/cases",
        "/api/v1/users",
        "/api/v1/reports",
        "/api/v1/comparisons/00000000-0000-0000-0000-000000000001",
    ):
        resp = raw_client.get(path)
        assert resp.status_code == 401, f"{path} should require auth"


def test_viewer_can_read_but_not_write(raw_client, staff, case):
    _, viewer, _, _ = staff
    headers = _headers(viewer)

    assert raw_client.get("/api/v1/cases", headers=headers).status_code == 200
    assert raw_client.get(f"/api/v1/cases/{case.id}", headers=headers).status_code == 200
    assert raw_client.get("/api/v1/dashboard/stats", headers=headers).status_code == 200

    create_case = raw_client.post(
        "/api/v1/cases",
        json={"title": "Nope", "case_number": "CASE-NOPE"},
        headers=headers,
    )
    assert create_case.status_code == 403
    assert raw_client.get("/api/v1/users", headers=headers).status_code == 403


def test_viewer_cannot_upload_evidence(raw_client, staff, case):
    _, viewer, _, case = staff
    resp = raw_client.post(
        "/api/v1/evidence/upload",
        data={"case_id": str(case.id)},
        files={"file": ("clip.mp4", FAKE_MP4, "video/mp4")},
        headers=_headers(viewer),
    )
    assert resp.status_code == 403


def test_investigator_can_create_case_and_upload(raw_client, staff, case):
    inv, viewer, _, case = staff
    headers = _headers(inv)

    created = raw_client.post(
        "/api/v1/cases",
        json={"title": "New Case"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["case_number"].startswith("CSE-")

    uploaded = raw_client.post(
        "/api/v1/evidence/upload",
        data={"case_id": str(case.id)},
        files={"file": ("clip.mp4", FAKE_MP4, "video/mp4")},
        headers=headers,
    )
    assert uploaded.status_code == 201


def test_investigator_cannot_manage_users_or_delete(raw_client, staff, case):
    inv, _, _, case = staff
    headers = _headers(inv)
    assert (
        raw_client.post(
            "/api/v1/users",
            json={"name": "X", "email": "x@test.local", "password": PASSWORD},
            headers=headers,
        ).status_code
        == 403
    )
    assert raw_client.delete(f"/api/v1/evidence/{case.id}", headers=headers).status_code == 403


def test_admin_can_manage_users_and_delete(raw_client, staff, db_session):
    _, _, admin, case = staff
    headers = _headers(admin)

    listed = raw_client.get("/api/v1/users", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 3

    created = raw_client.post(
        "/api/v1/users",
        json={"name": "New Guy", "email": "new@test.local", "password": PASSWORD},
        headers=headers,
    )
    assert created.status_code == 201
    new_id = created.json()["id"]

    patched = raw_client.patch(
        f"/api/v1/users/{new_id}",
        json={"role": "investigator"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "investigator"

    upload = raw_client.post(
        "/api/v1/evidence/upload",
        data={"case_id": str(case.id)},
        files={"file": ("clip.mp4", FAKE_MP4, "video/mp4")},
        headers=headers,
    )
    assert upload.status_code == 201
    evidence_id = upload.json()["id"]

    deleted = raw_client.delete(f"/api/v1/evidence/{evidence_id}", headers=headers)
    assert deleted.status_code == 204

    audit = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "evidence.delete"))
        .scalars()
        .all()
    )
    assert len(audit) == 1
    assert audit[0].user_id == admin.id
