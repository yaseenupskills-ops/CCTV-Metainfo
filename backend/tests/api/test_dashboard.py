import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, CaseStatus
from app.models import Analysis, Case
from tests.helpers import FAKE_MP4, upload


def _make_analysis(db_session: Session, evidence_id: uuid.UUID, status: AnalysisStatus):
    db_session.add(
        Analysis(
            evidence_id=evidence_id,
            analysis_type="frame_sampling",
            status=status,
            params={},
        )
    )
    db_session.commit()


def test_dashboard_stats_empty(client: TestClient):
    resp = client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cases"] == {"total": 0, "open": 0, "closed": 0, "archived": 0}
    assert body["evidence"]["total"] == 0
    assert body["evidence"]["total_size"] == 0
    assert body["analyses"] == {"total": 0, "completed": 0, "pending": 0, "failed": 0}
    assert body["recent_evidence"] == []
    assert body["recent_activity"] == []


def test_dashboard_stats_aggregates(client: TestClient, case: Case, db_session: Session):
    closed = Case(
        case_number="CASE-T2",
        title="Closed",
        status=CaseStatus.CLOSED,
        investigator_id=case.investigator_id,
    )
    db_session.add(closed)
    db_session.commit()

    upload(client, case.id, FAKE_MP4)
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]

    _make_analysis(db_session, uuid.UUID(evidence_id), AnalysisStatus.COMPLETED)
    _make_analysis(db_session, uuid.UUID(evidence_id), AnalysisStatus.QUEUED)

    resp = client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    body = resp.json()

    assert body["cases"]["total"] == 2
    assert body["cases"]["open"] == 1
    assert body["cases"]["closed"] == 1

    assert body["evidence"]["total"] == 2
    assert body["evidence"]["total_size"] == 2 * len(FAKE_MP4)
    assert body["evidence"]["by_status"]["uploaded"] == 2

    assert body["analyses"]["total"] == 2
    assert body["analyses"]["completed"] == 1
    assert body["analyses"]["pending"] == 1
    assert body["analyses"]["failed"] == 0


def test_dashboard_stats_recent_evidence_limit(client: TestClient, case: Case):
    for i in range(6):
        upload(client, case.id, FAKE_MP4, filename=f"clip{i}.mp4")

    body = client.get("/api/v1/dashboard/stats").json()
    assert body["evidence"]["total"] == 6
    recent = body["recent_evidence"]
    assert len(recent) == 5
    recent_names = {item["original_filename"] for item in recent}
    assert recent_names.issubset({f"clip{i}.mp4" for i in range(6)})


def test_dashboard_stats_recent_activity(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    upload(client, case.id, FAKE_MP4)
    evidence_id = upload(client, case.id, sample_video.read_bytes(), filename="active.mp4").json()[
        "id"
    ]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    client.delete(f"/api/v1/evidence/{evidence_id}")

    body = client.get("/api/v1/dashboard/stats").json()
    actions = [entry["action"] for entry in body["recent_activity"]]
    assert len(actions) >= 3
    assert "evidence.metadata_extract" in actions
    assert "evidence.delete" in actions
    assert "evidence.upload" in actions


def test_dashboard_stats_hides_deleted_from_recent(client: TestClient, case: Case):
    upload(client, case.id, FAKE_MP4, filename="kept.mp4")
    deleted_id = upload(client, case.id, FAKE_MP4, filename="gone.mp4").json()["id"]
    client.delete(f"/api/v1/evidence/{deleted_id}")

    body = client.get("/api/v1/dashboard/stats").json()
    assert body["evidence"]["total"] == 2
    filenames = [item["original_filename"] for item in body["recent_evidence"]]
    assert filenames == ["kept.mp4"]
