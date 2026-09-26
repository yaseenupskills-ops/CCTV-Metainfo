import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AnalysisStatus, AnalysisType
from app.db.base import Base, JSONType, enum_values

if TYPE_CHECKING:
    from app.models.anomaly import Anomaly
    from app.models.evidence import Evidence


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("evidence.id"), index=True, nullable=False
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(
        sa.Enum(AnalysisType, native_enum=False, length=30, values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        sa.Enum(AnalysisStatus, native_enum=False, length=20, values_callable=enum_values),
        default=AnalysisStatus.QUEUED,
        nullable=False,
    )
    params: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    evidence: Mapped["Evidence"] = relationship(back_populates="analyses")
    anomalies: Mapped[list["Anomaly"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
