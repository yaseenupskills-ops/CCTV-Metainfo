"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'investigator', 'viewer')", name="ck_users_role"
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- cases ---
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_number", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("investigator_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'archived')", name="ck_cases_status"
        ),
    )
    op.create_index("ix_cases_case_number", "cases", ["case_number"], unique=True)

    # --- evidence ---
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("evidence_number", sa.String(length=50), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("stored_filename", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("sha512", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'hashed', 'metadata_extracted', 'analyzed', 'archived')",
            name="ck_evidence_status",
        ),
    )
    op.create_index("ix_evidence_case_id", "evidence", ["case_id"])
    op.create_index("ix_evidence_evidence_number", "evidence", ["evidence_number"], unique=True)

    # --- video_metadata ---
    op.create_table(
        "video_metadata",
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id"), primary_key=True),
        sa.Column("container_format", sa.String(length=50), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.Float(), nullable=True),
        sa.Column("frame_count", sa.BigInteger(), nullable=True),
        sa.Column("video_codec", sa.String(length=50), nullable=True),
        sa.Column("audio_codec", sa.String(length=50), nullable=True),
        sa.Column("bitrate", sa.BigInteger(), nullable=True),
        sa.Column("pixel_format", sa.String(length=50), nullable=True),
        sa.Column("stream_count", sa.Integer(), nullable=True),
        sa.Column("creation_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encoder", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )

    # --- analyses ---
    op.create_table(
        "analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("analysis_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "analysis_type IN ('hashing', 'metadata', 'video_structure', 'frame_sampling', "
            "'scene_change', 'comparison')",
            name="ck_analyses_analysis_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_analyses_status",
        ),
    )
    op.create_index("ix_analyses_evidence_id", "analyses", ["evidence_id"])

    # --- anomalies ---
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=True),
        sa.Column("anomaly_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_data", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_anomalies_severity",
        ),
    )
    op.create_index("ix_anomalies_analysis_id", "anomalies", ["analysis_id"])

    # --- comparisons ---
    op.create_table(
        "comparisons",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("original_evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("suspected_evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )

    # --- reports ---
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id"), nullable=True),
        sa.Column("comparison_id", sa.Uuid(), sa.ForeignKey("comparisons.id"), nullable=True),
        sa.Column("report_path", sa.String(length=1000), nullable=False),
        sa.Column("generated_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("reports")
    op.drop_table("comparisons")
    op.drop_table("anomalies")
    op.drop_table("analyses")
    op.drop_table("video_metadata")
    op.drop_table("evidence")
    op.drop_table("cases")
    op.drop_table("users")
