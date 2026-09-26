import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CaseStatus
from app.db.base import Base, enum_values

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.report import Report
    from app.models.user import User


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(sa.String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(
        sa.Enum(CaseStatus, native_enum=False, length=20, values_callable=enum_values),
        default=CaseStatus.OPEN,
        nullable=False,
    )
    investigator_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    investigator: Mapped["User | None"] = relationship(back_populates="cases")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case")
    reports: Mapped[list["Report"]] = relationship(back_populates="case")
