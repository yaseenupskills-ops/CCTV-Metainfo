import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, DbSession, StaffUser
from app.schemas.case import CaseCreate, CaseRead
from app.schemas.pagination import PaginatedResponse
from app.services.audit_service import AuditService
from app.services.case_service import create_case, list_cases
from app.services.evidence_service import get_case_or_404

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=PaginatedResponse[CaseRead])
def list_cases_endpoint(
    db: DbSession,
    _: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> PaginatedResponse[CaseRead]:
    """List cases with optional free-text search, newest first."""
    cases, total = list_cases(db, page=page, page_size=page_size, search=search)
    return PaginatedResponse[CaseRead](
        items=[CaseRead.model_validate(case) for case in cases],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.get("/{case_id}", response_model=CaseRead)
def get_case_endpoint(
    db: DbSession,
    _: CurrentUser,
    case_id: uuid.UUID,
) -> CaseRead:
    """Return a single case."""
    return CaseRead.model_validate(get_case_or_404(db, case_id))


@router.post("", response_model=CaseRead, status_code=201)
def create_case_endpoint(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    body: CaseCreate,
) -> CaseRead:
    """Create a new case (investigator or admin)."""
    case = create_case(db, body=body)
    AuditService.record(
        db,
        action="case.create",
        entity_type="case",
        entity_id=case.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"case_number": case.case_number, "title": case.title},
    )
    return CaseRead.model_validate(case)
