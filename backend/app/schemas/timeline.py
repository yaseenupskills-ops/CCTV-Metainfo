import uuid
from typing import Any, Literal

from pydantic import BaseModel

from app.core.enums import AnalysisStatus, AnalysisType


class TimelineSegment(BaseModel):
    """A contiguous slice of the video on the timeline.

    `normal` segments tile the duration between anomalies; `anomaly` segments
    are zero-width markers positioned at the event timestamp. When `kind` is
    `anomaly`, `event_index` references the matching entry in `events`.
    """

    kind: Literal["normal", "anomaly"]
    start: float
    end: float
    severity: str | None = None
    event_index: int | None = None


class TimelineEvent(BaseModel):
    """A single detected frame-difference event shown in the detail drawer."""

    timestamp: float
    severity: str
    detection_method: str
    diff_score: float
    prev_frame: int | None
    current_frame: int | None
    metrics: dict[str, Any]
    analysis_id: uuid.UUID
    analysis_type: AnalysisType


class TimelineResponse(BaseModel):
    evidence_id: uuid.UUID
    duration: float | None
    analysis_id: uuid.UUID | None
    analysis_status: AnalysisStatus | None
    segments: list[TimelineSegment]
    events: list[TimelineEvent]
