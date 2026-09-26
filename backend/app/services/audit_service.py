import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog, User


class AuditService:
    """Writes append-only audit log entries."""

    @staticmethod
    def record(
        db: Session,
        *,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def list_audit_logs(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Return {items: AuditLogRead[], page, page_size, total, total_pages}."""
        from sqlalchemy import func, select

        # The filters are assembled once and applied to both the page query and
        # the count query. Building them separately is what let the count drift
        # out of sync: date_from/date_to were added to the page query only, so
        # `total` counted the whole table and `total_pages` promised pages that
        # came back empty.
        conditions = []
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if entity_type is not None:
            conditions.append(AuditLog.entity_type == entity_type)
        if action is not None:
            conditions.append(AuditLog.action == action)
        if date_from is not None:
            conditions.append(AuditLog.timestamp >= date_from)
        if date_to is not None:
            conditions.append(AuditLog.timestamp <= date_to)

        stmt = (
            select(AuditLog)
            .join(User, AuditLog.user_id == User.id, isouter=True)
            .where(*conditions)
        )

        # The count needs no join: user_id is a foreign key, so the outer join
        # cannot duplicate an audit_logs row.
        count_stmt = select(func.count(AuditLog.id)).where(*conditions)

        total = db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(AuditLog.timestamp.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        rows = db.execute(stmt).scalars().all()
        items = [
            {
                "id": str(row.id),
                "user_id": str(row.user.id) if row.user else None,
                "user_name": row.user.name if row.user else None,
                "user_email": row.user.email if row.user else None,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id) if row.entity_id else None,
                "timestamp": row.timestamp.isoformat(),
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "details": row.details,
            }
            for row in rows
        ]

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }
