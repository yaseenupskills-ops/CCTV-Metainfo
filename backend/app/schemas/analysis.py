import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import AnalysisStatus, AnalysisType


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_type: AnalysisType
    params: dict[str, Any] = {}


class AnalysisStart(BaseModel):
    """Request body for starting an analysis on an evidence."""

    model_config = ConfigDict(extra="forbid")

    analysis_type: AnalysisType = AnalysisType.FRAME_SAMPLING
    sampling_rate: int | None = None
    threshold: float | None = None


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_id: uuid.UUID
    analysis_type: AnalysisType
    status: AnalysisStatus
    params: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class AnalysisDetail(AnalysisRead):
    result: dict[str, Any] | None
