from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, CaseStatus
from app.models import Analysis, AuditLog, Case, Evidence
from app.services.evidence_service import list_evidence


def _count_grouped(db: Session, model, column) -> dict:
    """Count rows grouped by an enum column, with zero values for every member."""
    rows = db.execute(select(column, func.count()).group_by(column)).all()
    totals = {member: 0 for member in column.type.enums}
    for value, count in rows:
        totals[value] = int(count)
    return totals


def get_dashboard_stats(db: Session) -> dict[str, Any]:
    """Compute aggregate dashboard statistics from the database."""
    case_totals = _count_grouped(db, Case, Case.status)
    evidence_totals = _count_grouped(db, Evidence, Evidence.status)
    analysis_totals = _count_grouped(db, Analysis, Analysis.status)

    evidence_size = db.execute(
        select(func.coalesce(func.sum(Evidence.file_size), 0)).select_from(Evidence)
    ).scalar_one()

    recent_evidence, _ = list_evidence(db, page=1, page_size=5)
    recent_activity = list(
        db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10)).scalars().all()
    )

    return {
        "cases": {
            "total": sum(case_totals.values()),
            "open": case_totals[CaseStatus.OPEN],
            "closed": case_totals[CaseStatus.CLOSED],
            "archived": case_totals[CaseStatus.ARCHIVED],
        },
        "evidence": {
            "total": sum(evidence_totals.values()),
            "total_size": int(evidence_size),
            "by_status": evidence_totals,
        },
        "analyses": {
            "total": sum(analysis_totals.values()),
            "completed": analysis_totals[AnalysisStatus.COMPLETED],
            "pending": analysis_totals[AnalysisStatus.QUEUED]
            + analysis_totals[AnalysisStatus.PROCESSING],
            "failed": analysis_totals[AnalysisStatus.FAILED],
        },
        "recent_evidence": recent_evidence,
        "recent_activity": recent_activity,
    }
