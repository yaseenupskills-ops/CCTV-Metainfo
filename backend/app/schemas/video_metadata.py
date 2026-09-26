import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class VideoMetadataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: uuid.UUID
    container_format: str | None
    duration: float | None
    width: int | None
    height: int | None
    frame_rate: float | None
    frame_count: int | None
    video_codec: str | None
    audio_codec: str | None
    bitrate: int | None
    pixel_format: str | None
    stream_count: int | None
    creation_time: datetime | None
    encoder: str | None
    analyzed_at: datetime


class VideoMetadataDetail(VideoMetadataRead):
    metadata_json: dict[str, Any]


class MetadataTaskAccepted(BaseModel):
    """Acknowledgment returned when metadata extraction is queued for a worker."""

    evidence_id: uuid.UUID
    status: str = "queued"
