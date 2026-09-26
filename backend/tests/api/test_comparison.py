import subprocess
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.forensic.media import resolve_ffmpeg
from app.models import AuditLog, Case
from tests.helpers import upload


def _upload_with_metadata(client: TestClient, case: Case, path: Path, filename: str) -> str:
    """Upload a real video and extract its metadata; return the evidence id."""
    evidence_id = upload(client, case.id, path.read_bytes(), filename=filename).json()["id"]
    resp = client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    assert resp.status_code == 200
    return evidence_id


def _compare(client: TestClient, original_id: str, suspected_id: str) -> dict:
    resp = client.post(
        "/api/v1/comparisons",
        json={
            "original_evidence_id": original_id,
            "suspected_evidence_id": suspected_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_comparison_same_file_is_identical(client: TestClient, case: Case, sample_video: Path):
    content = sample_video.read_bytes()
    original_id = upload(client, case.id, content, filename="original.mp4").json()["id"]
    suspected_id = upload(client, case.id, content, filename="suspected.mp4").json()["id"]
    client.post(f"/api/v1/evidence/{original_id}/metadata")
    client.post(f"/api/v1/evidence/{suspected_id}/metadata")

    body = _compare(client, original_id, suspected_id)

    summary = body["result"]["summary"]
    assert summary["identical"] is True
    assert summary["differences"] == 0
    assert summary["matches"] > 0
    fields = {f["field"]: f for f in body["result"]["fields"]}
    assert fields["sha256"]["status"] == "match"
    assert fields["file_size"]["status"] == "match"
    assert fields["width"]["status"] == "match"


def test_comparison_detects_resolution_and_fps_difference(
    client: TestClient, case: Case, video_factory
):
    low_res = _upload_with_metadata(
        client, case, video_factory(duration=2, fps=10, size="320x240"), "low.mp4"
    )
    high_res = _upload_with_metadata(
        client, case, video_factory(duration=2, fps=15, size="640x480"), "high.mp4"
    )

    body = _compare(client, low_res, high_res)

    summary = body["result"]["summary"]
    assert summary["identical"] is False
    assert summary["differences"] >= 1
    fields = {f["field"]: f for f in body["result"]["fields"]}
    assert fields["width"]["status"] == "difference"
    assert fields["height"]["status"] == "difference"
    assert fields["frame_rate"]["status"] == "difference"


def test_comparison_detects_trimmed_copy(client: TestClient, case: Case, video_factory):
    full = _upload_with_metadata(client, case, video_factory(duration=3, fps=10), "full.mp4")
    trimmed = _upload_with_metadata(client, case, video_factory(duration=1, fps=10), "trimmed.mp4")

    body = _compare(client, full, trimmed)

    summary = body["result"]["summary"]
    assert summary["identical"] is False
    fields = {f["field"]: f for f in body["result"]["fields"]}
    assert fields["duration"]["status"] == "difference"
    assert fields["frame_count"]["status"] == "difference"
    assert fields["sha256"]["status"] == "difference"


def test_comparison_detects_reencoded_copy(
    client: TestClient, case: Case, video_factory, tmp_path: Path
):
    base = _upload_with_metadata(client, case, video_factory(duration=2, fps=10), "base.mp4")
    reencoded_path = _reencode_with_bitrate(
        video_factory(duration=2, fps=10), tmp_path / "reencoded.mp4", "500k"
    )
    reencoded = _upload_with_metadata(client, case, reencoded_path, "reencoded.mp4")

    body = _compare(client, base, reencoded)

    summary = body["result"]["summary"]
    assert summary["identical"] is False
    fields = {f["field"]: f for f in body["result"]["fields"]}
    assert fields["bitrate"]["status"] == "difference"
    assert fields["file_size"]["status"] == "difference"
    assert fields["duration"]["status"] == "match"


def _reencode_with_bitrate(src: Path, destination: Path, bitrate: str) -> Path:
    ffmpeg = resolve_ffmpeg()
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-b:v",
            bitrate,
            "-pix_fmt",
            "yuv420p",
            str(destination),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not destination.exists():
        pytest.skip("Could not re-encode sample video")
    return destination


def test_comparison_missing_metadata_marked_not_available(
    client: TestClient, case: Case, sample_video: Path
):
    content = sample_video.read_bytes()
    original_id = upload(client, case.id, content, filename="a.mp4").json()["id"]
    suspected_id = upload(client, case.id, content, filename="b.mp4").json()["id"]
    client.post(f"/api/v1/evidence/{original_id}/metadata")

    body = _compare(client, original_id, suspected_id)

    fields = {f["field"]: f for f in body["result"]["fields"]}
    assert fields["width"]["status"] == "not_available"
    assert fields["duration"]["status"] == "not_available"
    # Hash/size comparison still works without metadata.
    assert fields["sha256"]["status"] == "match"


def test_comparison_get_returns_stored(client: TestClient, case: Case, sample_video: Path):
    content = sample_video.read_bytes()
    original_id = upload(client, case.id, content, filename="a.mp4").json()["id"]
    suspected_id = upload(client, case.id, content, filename="b.mp4").json()["id"]

    created = _compare(client, original_id, suspected_id)
    resp = client.get(f"/api/v1/comparisons/{created['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == created["id"]
    assert body["result"]["summary"]["identical"] is True
    assert body["original_evidence_id"] == original_id


def test_comparison_unknown_evidence_404(client: TestClient, case: Case, sample_video: Path):
    known_id = upload(client, case.id, sample_video.read_bytes(), filename="a.mp4").json()["id"]
    resp = client.post(
        "/api/v1/comparisons",
        json={
            "original_evidence_id": known_id,
            "suspected_evidence_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 404


def test_comparison_get_unknown_404(client: TestClient):
    resp = client.get(f"/api/v1/comparisons/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_comparison_writes_audit_log(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    content = sample_video.read_bytes()
    original_id = upload(client, case.id, content, filename="a.mp4").json()["id"]
    suspected_id = upload(client, case.id, content, filename="b.mp4").json()["id"]

    body = _compare(client, original_id, suspected_id)

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "comparison.create")
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.entity_id == uuid.UUID(body["id"])
    assert entry.details["summary"]["identical"] is True
