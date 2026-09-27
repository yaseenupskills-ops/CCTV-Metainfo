"""The ORM-level guard on audit_logs, and the gap it leaves.

app/models/audit_log.py registers before_update / before_delete listeners that
raise. That covers every write that goes through the ORM, which is the normal
path, but it is not the same thing as database-enforced immutability: a raw SQL
statement, a psql session, or any other client with a connection is unaffected.

These tests pin down what the ORM guard does and, just as importantly, document
what it does not do, so the Postgres trigger in migration 0004 has a clear
purpose rather than looking redundant.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import hash_password
from app.models import AuditLog, User


def _hex_id(value: uuid.UUID) -> str:
    """The id as SQLite stores it: CHAR(32) hex, no dashes."""
    return value.hex


def _stored_action(db: Session, value: uuid.UUID) -> str:
    """Read the row with SQL, bypassing the identity map."""
    return db.execute(
        text("SELECT action FROM audit_logs WHERE id = :id"), {"id": _hex_id(value)}
    ).scalar_one()


@pytest.fixture()
def entry(db_session: Session) -> AuditLog:
    log = AuditLog(
        user_id=None,
        action="test.action",
        entity_type="test",
        details={"note": "original"},
    )
    db_session.add(log)
    db_session.commit()
    return log


# --- the ORM guard works -------------------------------------------------


def test_orm_update_is_blocked(db_session: Session, entry: AuditLog):
    entry.action = "tampered"

    with pytest.raises(ArgumentError, match="immutable"):
        db_session.commit()
    db_session.rollback()


def test_orm_delete_is_blocked(db_session: Session, entry: AuditLog):
    db_session.delete(entry)

    with pytest.raises(ArgumentError, match="immutable"):
        db_session.commit()
    db_session.rollback()


def test_blocked_update_leaves_the_row_intact(db_session: Session, entry: AuditLog):
    original = entry.action
    entry.action = "tampered"

    with pytest.raises(ArgumentError):
        db_session.commit()
    db_session.rollback()

    db_session.expire_all()
    assert db_session.get(AuditLog, entry.id).action == original


def test_insert_is_allowed(db_session: Session):
    log = AuditLog(action="test.insert", entity_type="test")
    db_session.add(log)
    db_session.commit()  # must not raise

    assert log.id is not None


# --- and this is the gap the trigger fills -------------------------------


def test_raw_sql_update_bypasses_the_orm_guard(db_session: Session, entry: AuditLog):
    """Documents the limitation the Postgres trigger exists to close.

    On SQLite the ORM listeners do not fire for text() statements, and the same
    is true on Postgres. This is why the unit suite cannot be the only place
    immutability is verified: it is the Postgres-backed tier that proves the
    database itself refuses the write.
    """
    db_session.execute(
        text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"),
        {"id": _hex_id(entry.id)},
    )
    db_session.commit()

    assert _stored_action(db_session, entry.id) == "tampered"


def test_raw_sql_delete_bypasses_the_orm_guard(db_session: Session, entry: AuditLog):
    db_session.execute(
        text("DELETE FROM audit_logs WHERE id = :id"), {"id": _hex_id(entry.id)}
    )
    db_session.commit()

    # Counted in SQL rather than via the identity map, which would still be
    # holding the deleted instance.
    remaining = db_session.execute(
        text("SELECT COUNT(*) FROM audit_logs WHERE id = :id"),
        {"id": _hex_id(entry.id)},
    ).scalar_one()
    assert remaining == 0


def test_a_user_relation_is_preserved_in_the_entry(db_session: Session):
    """A non-null user_id is a normal case, not an edge case."""
    user = User(
        name="Officer",
        email=f"officer-{uuid.uuid4().hex[:8]}@test.local",
        password_hash=hash_password("Passw0rd!x"),
        role=UserRole.INVESTIGATOR,
    )
    db_session.add(user)
    db_session.commit()

    log = AuditLog(
        user_id=user.id, action="auth.login", entity_type="user", details={}
    )
    db_session.add(log)
    db_session.commit()

    assert log.user is not None
    assert log.user.email == user.email
