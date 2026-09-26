import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import EvidenceStatus
from app.schemas.analysis import AnalysisRead
from app.schemas.video_metadata import VideoMetadataRead


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    evidence_number: str
    original_filename: str
    file_size: int
    mime_type: str
    sha256: str | None
    sha512: str | None
    hash_calculated_at: datetime | None
    status: EvidenceStatus
    uploaded_by: uuid.UUID
    uploaded_at: datetime


class EvidenceListItem(BaseModel):
    """A row in the evidence list, joined with its case for display."""

    id: uuid.UUID
    evidence_number: str
    case_id: uuid.UUID
    case_number: str | None
    case_title: str | None
    original_filename: str
    file_size: int
    mime_type: str
    sha256: str | None
    status: EvidenceStatus
    uploaded_at: datetime


class EvidenceDetail(EvidenceRead):
    video_metadata: VideoMetadataRead | None = None
    analyses: list[AnalysisRead] = []


class HashCalculation(BaseModel):
    algorithm: str
    hash: str
    file_size: int
    calculated_at: datetime


class HashResponse(BaseModel):
    evidence_id: uuid.UUID
    calculations: list[HashCalculation]
