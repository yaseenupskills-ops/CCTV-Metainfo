from datetime import timedelta

from sqlalchemy import select

from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, User


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


def _headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def test_login_success(raw_client, db_session):
    _make_user(db_session, password="Passw0rd!x")
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": "officer@test.local", "password": "Passw0rd!x"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "officer@test.local"
    assert body["user"]["role"] == "viewer"


def test_login_lowercases_email(raw_client, db_session):
    _make_user(db_session, email="Officer@Test.Local")
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": "officer@test.local", "password": "Passw0rd!x"},
    )
    assert resp.status_code == 200


def test_login_wrong_password_is_401_and_audited(raw_client, db_session):
    _make_user(db_session)
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


def test_login_unknown_email_is_401(raw_client, db_session):
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.local", "password": "Passw0rd!x"},
    )
    assert resp.status_code == 401


def test_login_records_successful_audit(raw_client, db_session):
    user = _make_user(db_session)
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Passw0rd!x"},
    )
    assert resp.status_code == 200
    logged = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "auth.login")).scalars().all()
    )
    assert len(logged) == 1
    assert logged[0].user_id == user.id
    assert logged[0].entity_id == user.id


def test_me_returns_authenticated_user(client, admin_user):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == admin_user.email
    assert body["role"] == "admin"
    assert body["id"] == str(admin_user.id)


def test_me_without_token_is_401(raw_client):
    resp = raw_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token_is_401(raw_client):
    resp = raw_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


def test_me_with_expired_token_is_401(raw_client, db_session):
    user = _make_user(db_session)
    token = create_access_token(user.id, user.role.value, expires_delta=timedelta(minutes=-5))
    resp = raw_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
