import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuditLog, Case, Evidence, VideoMetadata
from tests.helpers import FAKE_MP4, upload


def test_metadata_endpoint_normalizes_fields(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    resp = upload(client, case.id, sample_video.read_bytes(), filename="sample.mp4")
    assert resp.status_code == 201
    evidence_id = resp.json()["id"]

    meta_resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert meta_resp.status_code == 200
    body = meta_resp.json()

    assert body["evidence_id"] == evidence_id
    assert body["status"] == "queued"

    db_session.expire_all()
    metadata = db_session.get(VideoMetadata, uuid.UUID(evidence_id))
    assert metadata is not None
    assert metadata.width == 320
    assert metadata.height == 240
    assert metadata.video_codec == "h264"
    assert metadata.duration == pytest.approx(1.0, abs=0.1)
    assert metadata.frame_rate == pytest.approx(10.0, abs=0.1)
    assert metadata.container_format is not None
    assert metadata.pixel_format == "yuv420p"
    assert metadata.metadata_json["format"]["format_name"] is not None


def test_metadata_endpoint_stores_raw_json_and_structure(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    evidence_id = uuid.UUID(
        upload(client, case.id, sample_video.read_bytes(), filename="sample.mp4").json()["id"]
    )

    resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert resp.status_code == 200

    db_session.expire_all()
    metadata = db_session.get(VideoMetadata, evidence_id)
    assert metadata is not None
    assert metadata.metadata_json["format"]["format_name"] is not None
    structure = metadata.metadata_json["structure"]
    assert structure["keyframe_count"] >= 1
    assert structure["frame_count_probed"] >= 1


def test_metadata_endpoint_updates_evidence_status(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    evidence_id = uuid.UUID(
        upload(client, case.id, sample_video.read_bytes(), filename="sample.mp4").json()["id"]
    )

    client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    db_session.expire_all()
    evidence = db_session.get(Evidence, evidence_id)
    assert evidence is not None
    assert evidence.status.value == "metadata_extracted"


def test_metadata_endpoint_writes_audit_log(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    evidence_id = upload(client, case.id, sample_video.read_bytes(), filename="sample.mp4").json()[
        "id"
    ]

    client.post(f"/api/v1/evidence/{evidence_id}/metadata")

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "evidence.metadata_extract")
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.entity_id == uuid.UUID(evidence_id)


def test_metadata_endpoint_unknown_evidence_404(client: TestClient):
    resp = client.post(f"/api/v1/evidence/{uuid.uuid4()}/metadata")
    assert resp.status_code == 404


def test_metadata_endpoint_fails_on_fake_video(client: TestClient, case: Case):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]
    resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert resp.status_code == 500


def test_metadata_endpoint_missing_ffprobe(
    client: TestClient, case: Case, sample_video: Path, monkeypatch
):
    monkeypatch.setattr(settings, "ffprobe_path", "nonexistent-ffprobe-binary")
    evidence_id = upload(client, case.id, sample_video.read_bytes(), filename="sample.mp4").json()[
        "id"
    ]

    resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert resp.status_code == 500
