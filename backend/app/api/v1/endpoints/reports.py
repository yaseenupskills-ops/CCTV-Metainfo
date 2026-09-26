import uuid
from math import ceil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, StaffUser
from app.core.exceptions import NotFoundError
from app.models import Report
from app.schemas.pagination import PaginatedResponse
from app.schemas.report import ReportCreate, ReportRead
from app.services.audit_service import AuditService
from app.services.report_service import generate_report, get_report_or_404

router = APIRouter(prefix="/reports", tags=["reports"])


def _to_report_read(report: Report) -> ReportRead:
    read = ReportRead.model_validate(report)
    read.case_number = report.case.case_number if report.case else None
    read.evidence_number = report.evidence.evidence_number if report.evidence else None
    return read


@router.post("", response_model=ReportRead, status_code=201)
def create_report(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    body: ReportCreate,
) -> ReportRead:
    """Generate a PDF forensic report and persist the report record.

    Gathers case, evidence, analysis, timeline, anomaly-score, comparison, and
    audit data into a printable PDF. The report separates OBSERVED FACTS from
    AUTOMATED INTERPRETATIONS and reserves space for investigator conclusions.
    """
    report = generate_report(
        db,
        case_id=body.case_id,
        evidence_id=body.evidence_id,
        comparison_id=body.comparison_id,
        generated_by=actor.id,
    )

    AuditService.record(
        db,
        action="report.create",
        entity_type="report",
        entity_id=report.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={
            "case_id": str(body.case_id),
            "evidence_id": str(body.evidence_id) if body.evidence_id else None,
            "comparison_id": str(body.comparison_id) if body.comparison_id else None,
        },
    )

    return _to_report_read(report)


@router.get("", response_model=PaginatedResponse[ReportRead])
def list_reports(
    db: DbSession,
    _: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    case_id: uuid.UUID | None = None,
) -> PaginatedResponse[ReportRead]:
    """List generated reports with optional case filter, newest first."""
    stmt = (
        select(Report)
        .options(joinedload(Report.case), joinedload(Report.evidence))
        .order_by(Report.generated_at.desc())
    )
    if case_id is not None:
        stmt = stmt.where(Report.case_id == case_id)

    count_stmt = select(func.count(Report.id))
    if case_id is not None:
        count_stmt = count_stmt.where(Report.case_id == case_id)
    total = db.execute(count_stmt).scalar_one()

    items = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()

    return PaginatedResponse[ReportRead](
        items=[_to_report_read(report) for report in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    db: DbSession,
    _: CurrentUser,
    report_id: uuid.UUID,
) -> ReportRead:
    """Return a previously generated report record."""
    return _to_report_read(get_report_or_404(db, report_id))


@router.get("/{report_id}/download")
def download_report(
    db: DbSession,
    _: CurrentUser,
    report_id: uuid.UUID,
) -> FileResponse:
    """Download the generated PDF file for a report."""
    report = get_report_or_404(db, report_id)
    path = Path(report.report_path)
    if not path.is_file():
        raise NotFoundError("Report file is missing from storage")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"forensic-report-{report.id}.pdf",
    )
