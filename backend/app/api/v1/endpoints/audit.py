import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, StaffUser
from app.schemas.audit_log import AuditLogRead
from app.schemas.pagination import PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=PaginatedResponse[AuditLogRead])
def list_audit_logs(
    db: DbSession,
    _: StaffUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PaginatedResponse[AuditLogRead]:
    """Admin-only: list audit logs with filters and pagination."""
    result = AuditService.list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        entity_type=entity_type,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedResponse[AuditLogRead](
        items=result["items"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    )
