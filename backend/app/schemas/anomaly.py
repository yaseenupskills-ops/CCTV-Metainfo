import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import Severity
from app.forensic.scoring import AnomalyCategory


class AnomalyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    timestamp: float | None
    anomaly_type: str
    severity: Severity
    confidence: float | None
    description: str
    evidence_data: dict[str, Any]


class ScoringFactorRead(BaseModel):
    name: str
    label: str
    max_points: int
    points: int
    reason: str


class AnomalyScoreRead(BaseModel):
    evidence_id: uuid.UUID
    analysis_id: uuid.UUID | None = None
    score: int | None = None
    category: AnomalyCategory | None = None
    factors: list[ScoringFactorRead] = []
    computed_at: datetime | None = None
