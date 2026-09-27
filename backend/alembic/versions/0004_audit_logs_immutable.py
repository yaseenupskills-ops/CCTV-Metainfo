"""enforce audit log immutability in the database

The ORM raises on update and delete of an AuditLog, but that only protects the
application. Anything else holding a connection to the database can still
UPDATE or DELETE audit rows, which is the one table in this schema whose
tamper-evidence matters most.

This adds a BEFORE UPDATE OR DELETE trigger that raises. Alembic is not exempt:
`alembic downgrade` drops the trigger, which is DDL and is not blocked, so the
migration remains reversible.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-17

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TRIGGER = "audit_logs_immutable"
_FUNCTION = "audit_logs_reject_mutation"

# A short, opaque message: the trigger fires for any caller, and a verbose
# message would tell someone probing the table what protection it has.
_RAISE = "RAISE EXCEPTION 'audit_logs rows are append-only'"

# Detached so it can be dropped independently of the trigger itself.
_CREATE_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {_FUNCTION}() RETURNS trigger AS $$
BEGIN
    {_RAISE};
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    # Postgres-only. The test suite and any SQLite tooling rely on the ORM-level
    # guard in app/models/audit_log.py instead.
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(_CREATE_FUNCTION)
    op.execute(
        f"CREATE TRIGGER {_TRIGGER} BEFORE UPDATE OR DELETE ON audit_logs "
        f"FOR EACH ROW EXECUTE FUNCTION {_FUNCTION}()"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER} ON audit_logs")
    op.execute(f"DROP FUNCTION IF EXISTS {_FUNCTION}()")
