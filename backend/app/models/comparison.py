import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.user import User


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    original_evidence_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("evidence.id"), nullable=False
    )
    suspected_evidence_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("evidence.id"), nullable=False
    )
    result: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    original_evidence: Mapped["Evidence"] = relationship(
        back_populates="comparisons_as_original", foreign_keys=[original_evidence_id]
    )
    suspected_evidence: Mapped["Evidence"] = relationship(
        back_populates="comparisons_as_suspected", foreign_keys=[suspected_evidence_id]
    )
    created_by_user: Mapped["User | None"] = relationship(back_populates="comparisons")
