"""add evidence.status 'deleted' to support soft delete

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-10

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS_ALL = (
    "status IN "
    "('uploaded', 'hashed', 'metadata_extracted', 'analyzed', 'archived', 'deleted')"
)
_STATUS_PRE_DELETE = (
    "status IN ('uploaded', 'hashed', 'metadata_extracted', 'analyzed', 'archived')"
)


def upgrade() -> None:
    op.drop_constraint("ck_evidence_status", "evidence", type_="check")
    op.create_check_constraint("ck_evidence_status", "evidence", _STATUS_ALL)


def downgrade() -> None:
    op.drop_constraint("ck_evidence_status", "evidence", type_="check")
    op.create_check_constraint("ck_evidence_status", "evidence", _STATUS_PRE_DELETE)
