import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Case, Evidence, User, VideoMetadata
from app.services.comparison_service import _compare_value, compare_evidence


def _make_evidence(
    db: Session,
    case: Case,
    *,
    sha256: str | None = None,
    file_size: int = 1000,
) -> Evidence:
    uploader = db.query(User).first()
    assert uploader is not None
    evidence = Evidence(
        case_id=case.id,
        evidence_number=f"EVD-{uuid.uuid4().hex[:6].upper()}",
        original_filename="clip.mp4",
        stored_filename="stored.mp4",
        file_size=file_size,
        mime_type="video/mp4",
        storage_path="/tmp/clip.mp4",
        sha256=sha256,
        uploaded_by=uploader.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def _attach_metadata(db: Session, evidence: Evidence, **overrides) -> None:
    metadata = VideoMetadata(evidence_id=evidence.id, **overrides)
    db.add(metadata)
    db.commit()
    db.refresh(evidence)


def test_compare_value_match():
    result = _compare_value(field="width", label="Width", original=320, suspected=320)
    assert result["status"] == "match"
    assert result["note"] is None


def test_compare_value_difference():
    result = _compare_value(field="width", label="Width", original=320, suspected=640)
    assert result["status"] == "difference"
    assert result["note"] is not None


def test_compare_value_not_available_when_missing():
    result = _compare_value(field="width", label="Width", original=None, suspected=640)
    assert result["status"] == "not_available"
    result_both = _compare_value(field="width", label="Width", original=None, suspected=None)
    assert result_both["status"] == "not_available"


def test_compare_value_float_tolerance():
    result = _compare_value(
        field="duration",
        label="Duration",
        original=2.004,
        suspected=2.000,
        tolerance=0.05,
    )
    assert result["status"] == "match"


def test_compare_value_float_tolerance_exceeded():
    result = _compare_value(
        field="duration",
        label="Duration",
        original=2.10,
        suspected=1.00,
        tolerance=0.05,
    )
    assert result["status"] == "difference"


def test_compare_identical_evidence(db_session: Session, case: Case):
    original = _make_evidence(db_session, case, sha256="abc")
    suspected = _make_evidence(db_session, case, sha256="abc")
    for evidence in (original, suspected):
        _attach_metadata(
            db_session,
            evidence,
            duration=2.0,
            width=320,
            height=240,
            frame_rate=10.0,
            video_codec="h264",
            pixel_format="yuv420p",
        )

    comparison = compare_evidence(
        db_session, original_evidence_id=original.id, suspected_evidence_id=suspected.id
    )

    summary = comparison.result["summary"]
    assert summary["identical"] is True
    assert summary["differences"] == 0
    assert summary["matches"] > 0


def test_compare_identical_evidence_requires_hash_match(db_session: Session, case: Case):
    """Without a cryptographic hash match, files are never reported identical."""
    original = _make_evidence(db_session, case, sha256=None)
    suspected = _make_evidence(db_session, case, sha256=None)

    comparison = compare_evidence(
        db_session, original_evidence_id=original.id, suspected_evidence_id=suspected.id
    )

    summary = comparison.result["summary"]
    assert summary["identical"] is False
    assert summary["not_available"] > 0


def test_compare_detects_differences(db_session: Session, case: Case):
    original = _make_evidence(db_session, case, sha256="abc", file_size=1000)
    suspected = _make_evidence(db_session, case, sha256="def", file_size=2000)
    _attach_metadata(
        db_session,
        original,
        duration=10.0,
        width=320,
        height=240,
        frame_rate=25.0,
        video_codec="h264",
    )
    _attach_metadata(
        db_session,
        suspected,
        duration=5.0,
        width=640,
        height=480,
        frame_rate=15.0,
        video_codec="h265",
    )

    comparison = compare_evidence(
        db_session, original_evidence_id=original.id, suspected_evidence_id=suspected.id
    )

    fields = {f["field"]: f for f in comparison.result["fields"]}
    assert fields["sha256"]["status"] == "difference"
    assert fields["file_size"]["status"] == "difference"
    assert fields["duration"]["status"] == "difference"
    assert fields["width"]["status"] == "difference"
    assert fields["height"]["status"] == "difference"
    assert fields["frame_rate"]["status"] == "difference"
    assert fields["video_codec"]["status"] == "difference"
    assert comparison.result["summary"]["identical"] is False


def test_compare_missing_evidence_404(db_session: Session, case: Case):
    original = _make_evidence(db_session, case, sha256="abc")
    with pytest.raises(NotFoundError) as excinfo:
        compare_evidence(
            db_session, original_evidence_id=original.id, suspected_evidence_id=uuid.uuid4()
        )
    assert excinfo.value.status_code == 404
