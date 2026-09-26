import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import ComparisonFieldStatus


class ComparisonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_evidence_id: uuid.UUID
    suspected_evidence_id: uuid.UUID


class ComparisonField(BaseModel):
    """One compared property with a per-field verdict."""

    field: str
    label: str
    status: ComparisonFieldStatus
    original: Any = None
    suspected: Any = None
    note: str | None = None


class ComparisonSummary(BaseModel):
    matches: int
    differences: int
    not_available: int
    identical: bool


class ComparisonResult(BaseModel):
    fields: list[ComparisonField]
    summary: ComparisonSummary


class ComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_evidence_id: uuid.UUID
    suspected_evidence_id: uuid.UUID
    result: dict[str, Any]
    created_by: uuid.UUID | None
    created_at: datetime
