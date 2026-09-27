"""Postgres-backed immutability tests for audit_logs.

The unit suite runs on in-memory SQLite, which cannot express a trigger, and
`Base.metadata.create_all` never runs Alembic. So the guard that actually
protects the audit trail in production was entirely untested: the ORM hooks in
app/models/audit_log.py raise on update and delete, but they only apply to
code that goes through the ORM. A direct SQL statement, psql, or any other
client holding a connection could still rewrite history.

These tests run the real migration against a real Postgres and try to mutate an
audit row over raw SQL, which is the case the ORM hooks do not cover.

They are skipped unless TEST_DATABASE_URL points at a disposable Postgres
database. This is not optional coverage to wave away: if you can run Postgres,
run this.

    docker compose up -d postgres
    createdb cctv_test
    TEST_DATABASE_URL=postgresql+psycopg://cctv_user:...@localhost:5432/cctv_test \
        pytest tests/integration -m postgres

The database is dropped and recreated by the fixture, so point it at a
throwaway database only.
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.config import settings

pytestmark = pytest.mark.postgres


@contextmanager
def _alembic_url(url: str) -> Iterator[None]:
    """Point Alembic at `url` for the duration of the block.

    alembic/env.py does `config.set_main_option("sqlalchemy.url",
    settings.database_url)` on every run, which discards anything a caller set
    with set_main_option. Overriding the settings object is therefore the only
    way to redirect a migration, and the previous default points at the
    developer's own database in .env.
    """
    original = settings.database_url
    settings.database_url = url
    try:
        yield
    finally:
        settings.database_url = original


@pytest.fixture(scope="module")
def engine() -> Iterator:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping Postgres-backed tests")

    eng = create_engine(url, pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except DBAPIError as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"cannot reach TEST_DATABASE_URL: {exc}")

    # Start from an empty schema, then build it with the real migrations. This
    # is a throwaway database: never point TEST_DATABASE_URL at anything you
    # care about.
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    with _alembic_url(url):
        command.upgrade(Config("alembic.ini"), "head")

    yield eng

    # Leave the schema empty rather than migrated, so a stale trigger cannot
    # reject a later `alembic downgrade` run against the same database.
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    eng.dispose()


@pytest.fixture()
def db(engine) -> Iterator[Session]:
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _insert_audit_row(db: Session) -> uuid.UUID:
    """Insert an audit row with raw SQL, the way a third-party client would."""
    row_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO audit_logs (id, action, entity_type, details, timestamp) "
            "VALUES (:id, 'test.action', 'test', CAST(:details AS jsonb), now())"
        ),
        {"id": str(row_id), "details": '{"note": "original"}'},
    )
    db.commit()
    return row_id


# --- the trigger rejects mutation ----------------------------------------


def test_trigger_exists(db: Session):
    """Sanity check: the migration actually installed the trigger."""
    present = db.execute(
        text(
            "SELECT COUNT(*) FROM pg_trigger "
            "WHERE tgname = 'audit_logs_immutable' AND NOT tgisinternal"
        )
    ).scalar_one()
    assert present == 1


def test_raw_update_is_rejected(db: Session):
    """Raw SQL UPDATE must fail. The ORM hook cannot help here."""
    row_id = _insert_audit_row(db)

    with pytest.raises(DBAPIError) as exc:
        db.execute(
            text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"),
            {"id": str(row_id)},
        )
    db.rollback()

    assert "append-only" in str(exc.value)


def test_raw_delete_is_rejected(db: Session):
    row_id = _insert_audit_row(db)

    with pytest.raises(DBAPIError) as exc:
        db.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": str(row_id)})
    db.rollback()

    assert "append-only" in str(exc.value)


def test_bulk_update_is_rejected(db: Session):
    """A single statement rewriting the whole table must also fail."""
    _insert_audit_row(db)

    with pytest.raises(DBAPIError) as exc:
        db.execute(text("UPDATE audit_logs SET action = 'wiped'"))
    db.rollback()

    assert "append-only" in str(exc.value)


def test_rejected_update_leaves_the_row_intact(db: Session):
    """A refused mutation must not partially apply."""
    row_id = _insert_audit_row(db)

    with pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"),
            {"id": str(row_id)},
        )
    db.rollback()

    action = db.execute(
        text("SELECT action FROM audit_logs WHERE id = :id"), {"id": str(row_id)}
    ).scalar_one()
    assert action == "test.action"


# --- appending still works ------------------------------------------------


def test_insert_is_still_allowed(db: Session):
    """The trigger must not interfere with the normal write path."""
    row_id = _insert_audit_row(db)

    row = db.execute(
        text("SELECT action FROM audit_logs WHERE id = :id"), {"id": str(row_id)}
    ).scalar_one()
    assert row == "test.action"


def test_orm_write_path_still_works(db: Session):
    from app.services.audit_service import AuditService

    entry = AuditService.record(
        db, action="test.recorded", entity_type="test", details={"k": "v"}
    )

    assert entry.id is not None
    assert db.execute(
        text("SELECT COUNT(*) FROM audit_logs WHERE id = :id"),
        {"id": str(entry.id)},
    ).scalar_one() == 1


# --- downgrade is reversible ----------------------------------------------


def test_downgrade_removes_the_trigger(db: Session):
    """`alembic downgrade` must work, and mutation must be possible after it.

    Without this, an operator who needs to undo the migration would be stuck.
    """
    url = str(db.get_bind().url)
    cfg = Config("alembic.ini")

    try:
        with _alembic_url(url):
            command.downgrade(cfg, "0003")

        # Trigger gone.
        present = db.execute(
            text(
                "SELECT COUNT(*) FROM pg_trigger "
                "WHERE tgname = 'audit_logs_immutable' AND NOT tgisinternal"
            )
        ).scalar_one()
        assert present == 0

        # And the table is writable again.
        row_id = _insert_audit_row(db)
        db.execute(
            text("UPDATE audit_logs SET action = 'now allowed' WHERE id = :id"),
            {"id": str(row_id)},
        )
        db.commit()
    finally:
        # Restore head even if an assertion above failed, so a failing run does
        # not leave the trigger disabled for the next one.
        with _alembic_url(url):
            command.upgrade(cfg, "head")
