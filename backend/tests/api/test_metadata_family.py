"""Metadata extraction tests against the sample-video family."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, VideoMetadata
from tests.helpers import upload


def _upload_with_metadata(client: TestClient, case: Case, path: Path, filename: str) -> str:
    evidence_id = upload(client, case.id, path.read_bytes(), filename=filename).json()["id"]
    resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert resp.status_code == 200
    return evidence_id


def _metadata(db_session: Session, evidence_id: str) -> VideoMetadata:
    db_session.expire_all()
    metadata = db_session.execute(
        select(VideoMetadata).where(VideoMetadata.evidence_id == uuid.UUID(evidence_id))
    ).scalar_one_or_none()
    assert metadata is not None
    return metadata


def test_base_and_trimmed_durations(
    client: TestClient, case: Case, db_session, sample_video_family
):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    trimmed = _upload_with_metadata(client, case, sample_video_family["trimmed"], "trimmed.mp4")

    base_meta = _metadata(db_session, base)
    trimmed_meta = _metadata(db_session, trimmed)

    assert base_meta.duration == pytest.approx(4.0, abs=0.3)
    assert trimmed_meta.duration == pytest.approx(2.0, abs=0.3)


def test_resolution_variant_reported(
    client: TestClient, case: Case, db_session, sample_video_family
):
    evidence_id = _upload_with_metadata(
        client, case, sample_video_family["different_resolution"], "other.mp4"
    )
    metadata = _metadata(db_session, evidence_id)

    assert metadata.width == 640
    assert metadata.height == 480
    assert metadata.frame_rate == pytest.approx(10.0, abs=0.1)


def test_fps_variant_reported(
    client: TestClient, case: Case, db_session, sample_video_family
):
    evidence_id = _upload_with_metadata(
        client, case, sample_video_family["different_fps"], "other.mp4"
    )
    metadata = _metadata(db_session, evidence_id)

    assert metadata.frame_rate == pytest.approx(5.0, abs=0.1)
    assert metadata.frame_count is not None


def test_joined_clip_double_duration(
    client: TestClient, case: Case, db_session, sample_video_family
):
    evidence_id = _upload_with_metadata(client, case, sample_video_family["joined"], "joined.mp4")
    metadata = _metadata(db_session, evidence_id)

    assert metadata.duration == pytest.approx(8.0, abs=0.3)


def test_metadata_modified_exposes_injected_tags(
    client: TestClient, case: Case, db_session, sample_video_family
):
    evidence_id = _upload_with_metadata(
        client, case, sample_video_family["metadata_modified"], "modified.mp4"
    )
    metadata = _metadata(db_session, evidence_id)

    tags = metadata.metadata_json.get("format", {}).get("tags", {})
    assert tags.get("title") == "Modified evidence copy"
