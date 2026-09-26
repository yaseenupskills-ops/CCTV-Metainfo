import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType

if TYPE_CHECKING:
    from app.models.evidence import Evidence


class VideoMetadata(Base):
    __tablename__ = "video_metadata"

    evidence_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("evidence.id"), primary_key=True)
    container_format: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    duration: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    width: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    frame_rate: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    video_codec: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    bitrate: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    pixel_format: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    stream_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    creation_time: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    encoder: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    evidence: Mapped["Evidence"] = relationship(back_populates="video_metadata")
