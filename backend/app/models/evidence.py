import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EvidenceStatus
from app.db.base import Base, enum_values

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.case import Case
    from app.models.comparison import Comparison
    from app.models.report import Report
    from app.models.user import User
    from app.models.video_metadata import VideoMetadata


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("cases.id"), index=True, nullable=False
    )
    evidence_number: Mapped[str] = mapped_column(
        sa.String(50), unique=True, index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(sa.String(1000), nullable=False)
    sha256: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    sha512: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    hash_calculated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        sa.Enum(EvidenceStatus, native_enum=False, length=30, values_callable=enum_values),
        default=EvidenceStatus.UPLOADED,
        nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    case: Mapped["Case"] = relationship(back_populates="evidence")
    uploaded_by_user: Mapped["User"] = relationship(back_populates="evidence")
    video_metadata: Mapped["VideoMetadata | None"] = relationship(
        back_populates="evidence", uselist=False
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )
    comparisons_as_original: Mapped[list["Comparison"]] = relationship(
        back_populates="original_evidence", foreign_keys="Comparison.original_evidence_id"
    )
    comparisons_as_suspected: Mapped[list["Comparison"]] = relationship(
        back_populates="suspected_evidence", foreign_keys="Comparison.suspected_evidence_id"
    )
    reports: Mapped[list["Report"]] = relationship(back_populates="evidence")
