import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: uuid.UUID
    evidence_id: uuid.UUID | None = None
    comparison_id: uuid.UUID | None = None


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    evidence_id: uuid.UUID | None = None
    comparison_id: uuid.UUID | None = None
    generated_by: uuid.UUID
    generated_at: datetime

    case_number: str | None = None
    evidence_number: str | None = None


class ReportListItem(ReportRead):
    pass
