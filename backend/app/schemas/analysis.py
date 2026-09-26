import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import AnalysisStatus, AnalysisType
from app.services.analysis_summary import build_analysis_summary


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
    # Compact stand-in for `result`, so a list view can show what an analysis
    # found without downloading every event's per-frame metrics. None until the
    # analysis has produced a result.
    summary: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _attach_summary(cls, data: Any) -> Any:
        """Derive `summary` from the source row so no caller can forget it.

        `from_attributes` cannot do this on its own: the model exposes no
        `summary` column to read. Doing it in a validator covers the evidence
        list endpoint, the evidence detail payload and the analyze response
        together, plus any future caller. Validating from a mapping is left
        alone so an explicitly supplied summary still wins.
        """
        if isinstance(data, dict) or not hasattr(data, "analysis_type"):
            return data
        values = {
            name: getattr(data, name) for name in cls.model_fields if hasattr(data, name)
        }
        values["summary"] = build_analysis_summary(data)
        return values


class AnalysisDetail(AnalysisRead):
    result: dict[str, Any] | None
