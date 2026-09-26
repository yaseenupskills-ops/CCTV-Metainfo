"""Comparison integration tests using a family of related sample videos."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.models import Case
from tests.helpers import upload


def _upload_with_metadata(client: TestClient, case: Case, path: Path, filename: str) -> str:
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


def _fields(body: dict) -> dict:
    return {field["field"]: field for field in body["result"]["fields"]}


def test_identical_upload_of_base_is_identical(client: TestClient, case: Case, sample_video_family):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    copy = _upload_with_metadata(client, case, sample_video_family["base"], "copy.mp4")

    body = _compare(client, base, copy)

    assert body["result"]["summary"]["identical"] is True
    assert body["result"]["summary"]["differences"] == 0


def test_trimmed_copy_differs_in_duration_and_frame_count(
    client: TestClient, case: Case, sample_video_family
):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    trimmed = _upload_with_metadata(client, case, sample_video_family["trimmed"], "trimmed.mp4")

    body = _compare(client, base, trimmed)
    fields = _fields(body)

    assert fields["sha256"]["status"] == "difference"
    assert fields["duration"]["status"] == "difference"
    assert fields["frame_count"]["status"] == "difference"


def test_reencoded_copy_keeps_duration_but_differs_in_encoding(
    client: TestClient, case: Case, sample_video_family
):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    reencoded = _upload_with_metadata(
        client, case, sample_video_family["reencoded"], "reencoded.mp4"
    )

    body = _compare(client, base, reencoded)
    fields = _fields(body)

    assert fields["sha256"]["status"] == "difference"
    assert fields["file_size"]["status"] == "difference"
    assert fields["duration"]["status"] == "match"
    assert body["result"]["summary"]["identical"] is False


def test_different_resolution_copy_differs_in_dimensions(
    client: TestClient, case: Case, sample_video_family
):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    other = _upload_with_metadata(
        client, case, sample_video_family["different_resolution"], "other.mp4"
    )

    fields = _fields(_compare(client, base, other))

    assert fields["width"]["status"] == "difference"
    assert fields["height"]["status"] == "difference"
    assert fields["frame_rate"]["status"] == "match"


def test_different_fps_copy_differs_in_frame_rate(
    client: TestClient, case: Case, sample_video_family
):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    other = _upload_with_metadata(client, case, sample_video_family["different_fps"], "other.mp4")

    fields = _fields(_compare(client, base, other))

    assert fields["frame_rate"]["status"] == "difference"
    assert fields["frame_count"]["status"] == "difference"
    assert fields["width"]["status"] == "match"


def test_joined_copy_is_longer(client: TestClient, case: Case, sample_video_family):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    joined = _upload_with_metadata(client, case, sample_video_family["joined"], "joined.mp4")

    fields = _fields(_compare(client, base, joined))

    assert fields["sha256"]["status"] == "difference"
    assert fields["duration"]["status"] == "difference"


def test_metadata_modified_copy_still_differs_in_hash(
    client: TestClient, case: Case, sample_video_family
):
    base = _upload_with_metadata(client, case, sample_video_family["base"], "base.mp4")
    modified = _upload_with_metadata(
        client, case, sample_video_family["metadata_modified"], "modified.mp4"
    )

    fields = _fields(_compare(client, base, modified))

    assert fields["sha256"]["status"] == "difference"
