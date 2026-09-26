"""Import all models so they register on Base.metadata."""

from app.models.analysis import Analysis
from app.models.anomaly import Anomaly
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.comparison import Comparison
from app.models.evidence import Evidence
from app.models.report import Report
from app.models.user import User
from app.models.video_metadata import VideoMetadata

__all__ = [
    "Analysis",
    "Anomaly",
    "AuditLog",
    "Case",
    "Comparison",
    "Evidence",
    "Report",
    "User",
    "VideoMetadata",
]
