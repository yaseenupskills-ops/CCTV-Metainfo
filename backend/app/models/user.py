import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.db.base import Base, enum_values

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.case import Case
    from app.models.comparison import Comparison
    from app.models.evidence import Evidence
    from app.models.report import Report


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, native_enum=False, length=20, values_callable=enum_values),
        default=UserRole.VIEWER,
        nullable=False,
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

    cases: Mapped[list["Case"]] = relationship(back_populates="investigator")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="uploaded_by_user")
    comparisons: Mapped[list["Comparison"]] = relationship(back_populates="created_by_user")
    reports: Mapped[list["Report"]] = relationship(back_populates="generated_by_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
