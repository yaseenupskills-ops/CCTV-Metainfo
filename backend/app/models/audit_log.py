import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(sa.String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(sa.String(50), index=True, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), index=True, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    details: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")


# Mapper-level before_update / before_delete are called as
# (mapper, connection, target). The previous signature took two positional
# arguments, so the listener raised TypeError instead of the intended
# ArgumentError: the write was still refused, but with a message that pointed
# at the listener rather than at the immutability rule, and the guard was
# untested. It is also a convenient place to note that this only covers writes
# that go through the ORM; migration 0004 adds the database-level trigger that
# the unit suite cannot exercise.


@event.listens_for(AuditLog, "before_update")
def _audit_log_before_update(
    _mapper: type[AuditLog],
    _connection: sa.Connection,
    _target: AuditLog,
) -> None:
    raise ArgumentError("audit_logs are immutable and cannot be updated")


@event.listens_for(AuditLog, "before_delete")
def _audit_log_before_delete(
    _mapper: type[AuditLog],
    _connection: sa.Connection,
    _target: AuditLog,
) -> None:
    raise ArgumentError("audit_logs are immutable and cannot be deleted")
