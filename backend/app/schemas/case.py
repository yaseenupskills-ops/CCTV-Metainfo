import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CaseStatus


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    case_number: str | None = Field(default=None, min_length=1, max_length=50)
    investigator_id: uuid.UUID | None = None


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: CaseStatus | None = None
    investigator_id: uuid.UUID | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_number: str
    title: str
    description: str | None
    status: CaseStatus
    investigator_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
