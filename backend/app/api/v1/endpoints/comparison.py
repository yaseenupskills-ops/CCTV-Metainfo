import uuid

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession, StaffUser
from app.schemas.comparison import ComparisonCreate, ComparisonRead
from app.services.audit_service import AuditService
from app.services.comparison_service import (
    compare_evidence,
    get_comparison_or_404,
)

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=ComparisonRead, status_code=201)
def create_comparison(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    body: ComparisonCreate,
) -> ComparisonRead:
    """Compare an original evidence against a suspected copy.

    Compares file size, hashes, and technical properties extracted from both
    files' stored metadata. Each property is reported with a
    MATCH/DIFFERENCE/NOT_AVAILABLE verdict. Run metadata extraction on both
    evidence items first so technical properties are available to compare.
    """
    comparison = compare_evidence(
        db,
        original_evidence_id=body.original_evidence_id,
        suspected_evidence_id=body.suspected_evidence_id,
        created_by=actor.id,
    )

    AuditService.record(
        db,
        action="comparison.create",
        entity_type="comparison",
        entity_id=comparison.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={
            "original_evidence_id": str(body.original_evidence_id),
            "suspected_evidence_id": str(body.suspected_evidence_id),
            "summary": comparison.result["summary"],
        },
    )

    return ComparisonRead.model_validate(comparison)


@router.get("/{comparison_id}", response_model=ComparisonRead)
def get_comparison(
    db: DbSession,
    _: CurrentUser,
    comparison_id: uuid.UUID,
) -> ComparisonRead:
    """Return a previously stored comparison with its structured result."""
    return ComparisonRead.model_validate(get_comparison_or_404(db, comparison_id))
