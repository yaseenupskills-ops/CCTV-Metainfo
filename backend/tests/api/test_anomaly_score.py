import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Anomaly, Case
from tests.helpers import upload


def _upload(client: TestClient, case: Case, path: Path, filename: str) -> str:
    return upload(client, case.id, path.read_bytes(), filename=filename).json()["id"]


def _run_scene_change(client: TestClient, evidence_id: str) -> dict:
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1, "threshold": 0.5},
    )
    assert resp.status_code == 200
    return resp.json()


def _get_score(client: TestClient, evidence_id: str) -> dict:
    resp = client.get(f"/api/v1/evidence/{evidence_id}/anomaly-score")
    assert resp.status_code == 200
    return resp.json()


def test_scene_change_populates_anomaly_rows(
    client: TestClient, case: Case, scene_change_video_factory, db_session: Session
):
    video = scene_change_video_factory()
    evidence_id = _upload(client, case, video, "scene.mp4")

    body = _run_scene_change(client, evidence_id)

    anomalies = (
        db_session.execute(select(Anomaly).where(Anomaly.analysis_id == uuid.UUID(body["id"])))
        .scalars()
        .all()
    )
    assert len(anomalies) == len(body["result"]["events"]) >= 1
    anomaly = anomalies[0]
    assert anomaly.anomaly_type == "scene_change"
    assert anomaly.severity.value == anomaly.evidence_data["severity"]
    assert anomaly.confidence == anomaly.evidence_data["diff_score"]
    assert "frame difference" in anomaly.description
    assert anomaly.timestamp is not None


def test_scene_change_persists_score_on_result(
    client: TestClient, case: Case, scene_change_video_factory
):
    video = scene_change_video_factory()
    evidence_id = _upload(client, case, video, "scene.mp4")

    body = _run_scene_change(client, evidence_id)

    payload = body["result"]["anomaly_score"]
    assert set(payload) == {"score", "category", "factors", "computed_at"}
    assert payload["computed_at"] is not None
    assert isinstance(payload["score"], int)
    assert len(payload["factors"]) == 6
    names = {f["name"] for f in payload["factors"]}
    assert names == {
        "metadata_inconsistency",
        "duration_difference",
        "frame_discontinuity",
        "encoding_difference",
        "unnatural_frame_diff_cluster",
        "single_scene_changes",
    }


def test_anomaly_score_endpoint_returns_score(
    client: TestClient, case: Case, scene_change_video_factory
):
    video = scene_change_video_factory()
    evidence_id = _upload(client, case, video, "scene.mp4")
    analysis = _run_scene_change(client, evidence_id)

    body = _get_score(client, evidence_id)

    assert body["evidence_id"] == evidence_id
    assert body["analysis_id"] == analysis["id"]
    assert body["score"] == analysis["result"]["anomaly_score"]["score"]
    assert body["category"] == analysis["result"]["anomaly_score"]["category"]
    assert len(body["factors"]) == 6


def test_anomaly_score_endpoint_no_analysis(client: TestClient, case: Case, sample_video: Path):
    evidence_id = _upload(client, case, sample_video, "plain.mp4")

    body = _get_score(client, evidence_id)

    assert body["analysis_id"] is None
    assert body["score"] is None
    assert body["category"] is None
    assert body["factors"] == []
    assert body["computed_at"] is None


def test_anomaly_score_endpoint_unknown_evidence_404(client: TestClient):
    resp = client.get(f"/api/v1/evidence/{uuid.uuid4()}/anomaly-score")
    assert resp.status_code == 404


def test_score_reflects_duration_deviation_after_comparison(
    client: TestClient, case: Case, video_factory
):
    original = _upload(client, case, video_factory(duration=4, fps=10), "original.mp4")
    suspected = _upload(client, case, video_factory(duration=2, fps=10), "suspected.mp4")
    client.post(f"/api/v1/evidence/{original}/metadata")
    client.post(f"/api/v1/evidence/{suspected}/metadata")
    _run_scene_change(client, original)
    _run_scene_change(client, suspected)

    resp = client.post(
        "/api/v1/comparisons",
        json={
            "original_evidence_id": original,
            "suspected_evidence_id": suspected,
        },
    )
    assert resp.status_code == 201

    suspected_score = _get_score(client, suspected)
    duration_factor = next(
        f for f in suspected_score["factors"] if f["name"] == "duration_difference"
    )
    assert duration_factor["points"] >= 10
    assert suspected_score["analysis_id"] is not None
