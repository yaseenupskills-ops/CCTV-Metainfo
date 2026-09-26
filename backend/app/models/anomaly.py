import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import Severity
from app.db.base import Base, JSONType, enum_values

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("analyses.id"), index=True, nullable=False
    )
    # Seconds into the video (float); null if not time-anchored.
    timestamp: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    anomaly_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        sa.Enum(Severity, native_enum=False, length=20, values_callable=enum_values),
        default=Severity.MEDIUM,
        nullable=False,
    )
    confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    evidence_data: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    analysis: Mapped["Analysis"] = relationship(back_populates="anomalies")
