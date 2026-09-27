"""The audit log immutability migration, checked without a Postgres server.

tests/integration/test_audit_log_immutability.py proves the trigger actually
rejects mutation, but it is skipped unless TEST_DATABASE_URL points at a
disposable Postgres. These tests run everywhere, so a mistake in the migration
itself — a wrong trigger name, a missing RAISE, a dialect guard that fires on
the wrong engine — is caught in the default suite rather than only in the
Postgres tier.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0004_audit_logs_immutable.py"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0004", _MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Recorder:
    """Stands in for alembic.op, recording the SQL a migration would run."""

    def __init__(self, dialect_name: str) -> None:
        self.dialect_name = dialect_name
        self.statements: list[str] = []

    class _Dialect:
        def __init__(self, name: str) -> None:
            self.name = name

    class _Bind:
        def __init__(self, name: str) -> None:
            self.dialect = _Recorder._Dialect(name)

    def get_bind(self):
        return self._Bind(self.dialect_name)

    def execute(self, sql: str) -> None:
        self.statements.append(sql)


def _run(dialect_name: str, direction: str) -> list[str]:
    module = _load()
    recorder = _Recorder(dialect_name)
    module.op = recorder
    getattr(module, direction)()
    return recorder.statements


# --- revision wiring ------------------------------------------------------


def test_revises_the_previous_head():
    module = _load()
    assert module.revision == "0004"
    assert module.down_revision == "0003"


# --- Postgres path --------------------------------------------------------


def test_upgrade_creates_the_trigger_on_postgres():
    statements = _run("postgresql", "upgrade")
    joined = "\n".join(statements)

    assert any("CREATE TRIGGER audit_logs_immutable" in s for s in statements)
    assert "BEFORE UPDATE OR DELETE ON audit_logs" in joined
    assert "FOR EACH ROW" in joined
    assert "EXECUTE FUNCTION audit_logs_reject_mutation()" in joined


def test_upgrade_creates_the_guard_function_on_postgres():
    joined = "\n".join(_run("postgresql", "upgrade"))

    assert "CREATE OR REPLACE FUNCTION audit_logs_reject_mutation()" in joined
    assert "RETURNS trigger" in joined
    assert "LANGUAGE plpgsql" in joined


def test_the_function_raises_on_every_path():
    """A trigger that falls through to RETURN would silently allow the write."""
    joined = "\n".join(_run("postgresql", "upgrade"))

    assert "RAISE EXCEPTION" in joined
    assert "append-only" in joined
    # No RETURN means no fall-through, which is what makes the RAISE
    # unconditional.
    assert "RETURN " not in joined.replace("RETURNS", "")


def test_downgrade_drops_trigger_and_function():
    statements = _run("postgresql", "downgrade")
    joined = "\n".join(statements)

    assert "DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs" in joined
    assert "DROP FUNCTION IF EXISTS audit_logs_reject_mutation()" in joined


def test_downgrade_is_reversible():
    """Both directions emit SQL, so upgrade -> downgrade is a real round trip."""
    assert _run("postgresql", "upgrade")
    assert _run("postgresql", "downgrade")


# --- non-Postgres dialects are untouched ---------------------------------


@pytest.mark.parametrize("dialect", ["sqlite", "mysql"])
def test_upgrade_is_a_noop_off_postgres(dialect: str):
    """The default suite runs on SQLite and must not try to create a trigger."""
    assert _run(dialect, "upgrade") == []


@pytest.mark.parametrize("dialect", ["sqlite", "mysql"])
def test_downgrade_is_a_noop_off_postgres(dialect: str):
    assert _run(dialect, "downgrade") == []


# --- the trigger is the strongest guard -----------------------------------


def test_trigger_covers_both_update_and_delete():
    """Two separate mechanisms, or a hole for one of them."""
    joined = "\n".join(_run("postgresql", "upgrade"))
    assert "BEFORE UPDATE OR DELETE" in joined
