from datetime import datetime

from sqlalchemy.orm import Session

from app.core.enums import EvidenceStatus
from app.forensic.media import probe_video
from app.models import Evidence, VideoMetadata

_NORMALIZED_FIELDS = (
    "container_format",
    "duration",
    "width",
    "height",
    "frame_rate",
    "frame_count",
    "video_codec",
    "audio_codec",
    "bitrate",
    "pixel_format",
    "stream_count",
    "creation_time",
    "encoder",
)


def _int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _video_stream(probe_data: dict) -> dict | None:
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def _audio_stream(probe_data: dict) -> dict | None:
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream
    return None


def parse_frame_rate(stream: dict) -> float | None:
    """Parse an ffprobe frame-rate string such as '30000/1001'."""
    rate = stream.get("r_frame_rate") or stream.get("avg_frame_rate")
    if not rate or "/" not in rate:
        return None
    numerator, _, denominator = rate.partition("/")
    try:
        num = float(numerator)
        den = float(denominator)
    except ValueError:
        return None
    if not den:
        return None
    return num / den


def parse_creation_time(probe_data: dict) -> datetime | None:
    """Parse ffprobe creation_time ISO-8601 tag into a timezone-aware datetime."""
    tags = probe_data.get("format", {}).get("tags", {}) or {}
    value = tags.get("creation_time")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_metadata(probe_data: dict) -> dict:
    """Map raw ffprobe JSON to normalized VideoMetadata column values."""
    vstream = _video_stream(probe_data)
    astream = _audio_stream(probe_data)
    fmt = probe_data.get("format", {})
    fmt_tags = fmt.get("tags", {}) or {}
    vstream_tags = (vstream or {}).get("tags", {}) or {}

    duration = _float_or_none(fmt.get("duration"))
    if duration is None and vstream:
        duration = _float_or_none(vstream.get("duration"))

    bitrate = _int_or_none(fmt.get("bit_rate"))
    if bitrate is None and vstream:
        bitrate = _int_or_none(vstream.get("bit_rate"))

    return {
        "container_format": fmt.get("format_name"),
        "duration": duration,
        "width": vstream.get("width") if vstream else None,
        "height": vstream.get("height") if vstream else None,
        "frame_rate": parse_frame_rate(vstream) if vstream else None,
        "frame_count": _int_or_none(vstream.get("nb_frames")) if vstream else None,
        "video_codec": vstream.get("codec_name") if vstream else None,
        "audio_codec": astream.get("codec_name") if astream else None,
        "bitrate": bitrate,
        "pixel_format": vstream.get("pix_fmt") if vstream else None,
        "stream_count": len(probe_data.get("streams", [])),
        "creation_time": parse_creation_time(probe_data),
        "encoder": vstream_tags.get("encoder") or fmt_tags.get("encoder"),
    }


def extract_and_store_metadata(db: Session, evidence: Evidence) -> VideoMetadata:
    """Run ffprobe, normalize results, and persist VideoMetadata for an evidence."""
    probe_data = probe_video(evidence.storage_path)
    normalized = normalize_metadata(probe_data)

    metadata = db.get(VideoMetadata, evidence.id)
    if metadata is None:
        metadata = VideoMetadata(evidence_id=evidence.id)
        db.add(metadata)

    for field in _NORMALIZED_FIELDS:
        setattr(metadata, field, normalized[field])
    metadata.metadata_json = probe_data

    evidence.status = EvidenceStatus.METADATA_EXTRACTED
    db.add(evidence)
    return metadata
