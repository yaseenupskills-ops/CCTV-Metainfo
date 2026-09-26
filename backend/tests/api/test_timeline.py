import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, AnalysisType
from app.models import Analysis, Case
from tests.helpers import upload


def _upload(client: TestClient, case: Case, path: Path) -> str:
    return upload(client, case.id, path.read_bytes(), filename=path.name).json()["id"]


def test_timeline_empty_without_scene_change(client: TestClient, case: Case, sample_video: Path):
    evidence_id = _upload(client, case, sample_video)

    resp = client.get(f"/api/v1/evidence/{evidence_id}/timeline")
    assert resp.status_code == 200
    body = resp.json()

    assert body["evidence_id"] == evidence_id
    assert body["segments"] == []
    assert body["events"] == []
    assert body["analysis_id"] is None
    assert body["analysis_status"] is None


def test_timeline_builds_segments_from_scene_change(
    client: TestClient, case: Case, scene_change_video_factory
):
    video = scene_change_video_factory(duration_per_half=2.0, fps=10)
    evidence_id = _upload(client, case, video)

    analyze_resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1},
    )
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()
    assert len(analysis["result"]["events"]) >= 1

    resp = client.get(f"/api/v1/evidence/{evidence_id}/timeline")
    assert resp.status_code == 200
    body = resp.json()

    assert body["analysis_id"] == analysis["id"]
    assert body["analysis_status"] == "completed"
    assert len(body["events"]) >= 1

    event = body["events"][0]
    assert event["severity"] in {"low", "medium", "high"}
    assert event["detection_method"] == "frame_difference"
    assert event["analysis_id"] == analysis["id"]
    assert "metrics" in event

    segments = body["segments"]
    anomaly_segments = [s for s in segments if s["kind"] == "anomaly"]
    normal_segments = [s for s in segments if s["kind"] == "normal"]
    assert len(anomaly_segments) == len(body["events"])
    assert anomaly_segments[0]["event_index"] == 0
    assert anomaly_segments[0]["severity"] == event["severity"]
    assert len(normal_segments) >= 1

    # Events are ordered by timestamp.
    timestamps = [e["timestamp"] for e in body["events"]]
    assert timestamps == sorted(timestamps)
    # The first event lands at/near the black→white cut (~2s).
    assert timestamps[0] == pytest.approx(2.0, abs=0.2)


def test_timeline_reports_in_progress_analysis(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    evidence_id = _upload(client, case, sample_video)
    analysis = Analysis(
        evidence_id=uuid.UUID(evidence_id),
        analysis_type=AnalysisType.SCENE_CHANGE,
        status=AnalysisStatus.PROCESSING,
        params={"sampling_rate": 1},
    )
    db_session.add(analysis)
    db_session.commit()

    resp = client.get(f"/api/v1/evidence/{evidence_id}/timeline")
    assert resp.status_code == 200
    body = resp.json()

    assert body["analysis_id"] == str(analysis.id)
    assert body["analysis_status"] == "processing"
    assert body["events"] == []


def test_timeline_unknown_evidence_404(client: TestClient):
    resp = client.get(f"/api/v1/evidence/{uuid.uuid4()}/timeline")
    assert resp.status_code == 404
