import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.comparison import Comparison
    from app.models.evidence import Evidence
    from app.models.user import User


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("cases.id"), nullable=False)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("evidence.id"), nullable=True
    )
    comparison_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("comparisons.id"), nullable=True
    )
    report_path: Mapped[str] = mapped_column(sa.String(1000), nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    case: Mapped["Case"] = relationship(back_populates="reports")
    evidence: Mapped["Evidence | None"] = relationship(back_populates="reports")
    comparison: Mapped["Comparison | None"] = relationship()
    generated_by_user: Mapped["User"] = relationship(back_populates="reports")
