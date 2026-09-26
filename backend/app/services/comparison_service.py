"""Metadata + hash comparison between an original and a suspected evidence.

Compares a fixed set of integrity and technical properties. Every property is
reported per-field with a MATCH / DIFFERENCE / NOT_AVAILABLE verdict so results
are structured and explainable. A difference between two videos never implies
tampering on its own — it is a factual observation for expert interpretation.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import ComparisonFieldStatus
from app.models import Comparison, Evidence
from app.services.evidence_service import get_evidence_or_404

# Numeric fields compared with a small tolerance because FFmpeg reports
# floating-point values that can vary across probes of the same file.
_FLOAT_TOLERANCES: dict[str, float] = {
    "duration": 0.05,
    "frame_rate": 0.01,
}

_STRING_FIELDS = (
    "container_format",
    "video_codec",
    "audio_codec",
    "pixel_format",
    "encoder",
)


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _compare_value(
    *,
    field: str,
    label: str,
    original: Any,
    suspected: Any,
    tolerance: float | None = None,
) -> dict:
    """Compare a single property and produce a per-field verdict dict."""
    if original is None or suspected is None:
        return {
            "field": field,
            "label": label,
            "status": ComparisonFieldStatus.NOT_AVAILABLE,
            "original": _serialize(original),
            "suspected": _serialize(suspected),
            "note": "Value not available on one or both evidence items",
        }
    if tolerance is not None:
        equal = abs(float(original) - float(suspected)) <= tolerance
    else:
        equal = original == suspected
    return {
        "field": field,
        "label": label,
        "status": ComparisonFieldStatus.MATCH if equal else ComparisonFieldStatus.DIFFERENCE,
        "original": _serialize(original),
        "suspected": _serialize(suspected),
        "note": None if equal else f"{label} differs between the two files",
    }


def _integer_field(field: str, label: str, original: Any, suspected: Any) -> dict:
    return _compare_value(
        field=field,
        label=label,
        original=original,
        suspected=suspected,
    )


def _metadata_value(evidence: Evidence, attribute: str) -> Any:
    metadata = evidence.video_metadata
    if metadata is None:
        return None
    return getattr(metadata, attribute, None)


def compare_evidence(
    db: Session,
    *,
    original_evidence_id: uuid.UUID,
    suspected_evidence_id: uuid.UUID,
    created_by: uuid.UUID | None = None,
) -> Comparison:
    """Run a full comparison and persist the structured result.

    Compares file size and hashes from the evidence rows plus technical
    properties from each video_metadata row (extracted via FFprobe). Fields
    missing on either side are marked NOT_AVAILABLE rather than skipped.
    """
    original = get_evidence_or_404(db, original_evidence_id)
    suspected = get_evidence_or_404(db, suspected_evidence_id)

    fields: list[dict] = [
        _compare_value(
            field="file_size",
            label="File size",
            original=original.file_size,
            suspected=suspected.file_size,
        ),
        _compare_value(
            field="sha256",
            label="SHA-256 hash",
            original=original.sha256,
            suspected=suspected.sha256,
        ),
        _compare_value(
            field="sha512",
            label="SHA-512 hash",
            original=original.sha512,
            suspected=suspected.sha512,
        ),
        _compare_value(
            field="duration",
            label="Duration",
            original=_metadata_value(original, "duration"),
            suspected=_metadata_value(suspected, "duration"),
            tolerance=_FLOAT_TOLERANCES["duration"],
        ),
        _integer_field(
            "width",
            "Width",
            _metadata_value(original, "width"),
            _metadata_value(suspected, "width"),
        ),
        _integer_field(
            "height",
            "Height",
            _metadata_value(original, "height"),
            _metadata_value(suspected, "height"),
        ),
        _compare_value(
            field="frame_rate",
            label="Frame rate",
            original=_metadata_value(original, "frame_rate"),
            suspected=_metadata_value(suspected, "frame_rate"),
            tolerance=_FLOAT_TOLERANCES["frame_rate"],
        ),
        _integer_field(
            "frame_count",
            "Frame count",
            _metadata_value(original, "frame_count"),
            _metadata_value(suspected, "frame_count"),
        ),
        _compare_value(
            field="bitrate",
            label="Bitrate",
            original=_metadata_value(original, "bitrate"),
            suspected=_metadata_value(suspected, "bitrate"),
        ),
        _compare_value(
            field="creation_time",
            label="Creation time",
            original=_metadata_value(original, "creation_time"),
            suspected=_metadata_value(suspected, "creation_time"),
        ),
    ]
    for attribute in _STRING_FIELDS:
        fields.append(
            _compare_value(
                field=attribute,
                label=attribute.replace("_", " ").title(),
                original=_metadata_value(original, attribute),
                suspected=_metadata_value(suspected, attribute),
            )
        )

    matches = sum(1 for f in fields if f["status"] is ComparisonFieldStatus.MATCH)
    differences = sum(1 for f in fields if f["status"] is ComparisonFieldStatus.DIFFERENCE)
    not_available = sum(1 for f in fields if f["status"] is ComparisonFieldStatus.NOT_AVAILABLE)

    field_statuses = {f["field"]: f["status"] for f in fields}
    hash_verified = (
        field_statuses["sha256"] is ComparisonFieldStatus.MATCH
        or field_statuses["sha512"] is ComparisonFieldStatus.MATCH
    )

    result = {
        "fields": fields,
        "summary": {
            "matches": matches,
            "differences": differences,
            "not_available": not_available,
            # Byte-identical requires a cryptographic hash match plus no
            # observed differences. Matching size/metadata alone is not enough.
            "identical": differences == 0 and hash_verified,
        },
    }

    comparison = Comparison(
        original_evidence_id=original.id,
        suspected_evidence_id=suspected.id,
        result=result,
        created_by=created_by,
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)

    from app.services.anomaly_service import recompute_scores_for_comparison

    recompute_scores_for_comparison(db, comparison)
    return comparison


def get_comparison_or_404(db: Session, comparison_id: uuid.UUID) -> Comparison:
    comparison = db.get(Comparison, comparison_id)
    if comparison is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Comparison not found")
    return comparison
