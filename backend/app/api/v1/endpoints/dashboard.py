from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.audit_log import AuditLogRead
from app.schemas.dashboard import (
    AnalysisStats,
    CaseStats,
    DashboardStats,
    EvidenceStats,
)
from app.services.dashboard_service import get_dashboard_stats
from app.services.evidence_service import to_evidence_list_item

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbSession, _: CurrentUser) -> DashboardStats:
    """Aggregate dashboard statistics: cases, evidence, analyses, recent activity."""
    stats = get_dashboard_stats(db)
    return DashboardStats(
        cases=CaseStats(**stats["cases"]),
        evidence=EvidenceStats(**stats["evidence"]),
        analyses=AnalysisStats(**stats["analyses"]),
        recent_evidence=[to_evidence_list_item(e) for e in stats["recent_evidence"]],
        recent_activity=[AuditLogRead.model_validate(a) for a in stats["recent_activity"]],
    )
