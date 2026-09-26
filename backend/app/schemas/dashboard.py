from pydantic import BaseModel

from app.core.enums import EvidenceStatus
from app.schemas.audit_log import AuditLogRead
from app.schemas.evidence import EvidenceListItem


class CaseStats(BaseModel):
    total: int
    open: int
    closed: int
    archived: int


class EvidenceStats(BaseModel):
    total: int
    total_size: int
    by_status: dict[EvidenceStatus, int]


class AnalysisStats(BaseModel):
    total: int
    completed: int
    pending: int
    failed: int


class DashboardStats(BaseModel):
    cases: CaseStats
    evidence: EvidenceStats
    analyses: AnalysisStats
    recent_evidence: list[EvidenceListItem]
    recent_activity: list[AuditLogRead]
