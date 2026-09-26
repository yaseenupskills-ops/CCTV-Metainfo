import enum


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    VIEWER = "viewer"


class CaseStatus(enum.StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class EvidenceStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    HASHED = "hashed"
    METADATA_EXTRACTED = "metadata_extracted"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AnalysisType(enum.StrEnum):
    HASHING = "hashing"
    METADATA = "metadata"
    VIDEO_STRUCTURE = "video_structure"
    FRAME_SAMPLING = "frame_sampling"
    SCENE_CHANGE = "scene_change"
    COMPARISON = "comparison"


class AnalysisStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(enum.StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComparisonFieldStatus(enum.StrEnum):
    MATCH = "match"
    DIFFERENCE = "difference"
    NOT_AVAILABLE = "not_available"
