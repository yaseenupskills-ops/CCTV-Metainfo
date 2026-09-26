import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, AnalysisType
from app.models import Analysis, AuditLog, Case, Evidence
from tests.helpers import FAKE_MP4, upload


def _make_analysis(db_session: Session, evidence_id: uuid.UUID, **kwargs) -> Analysis:
    analysis = Analysis(
        evidence_id=evidence_id,
        analysis_type=kwargs.get("analysis_type", AnalysisType.FRAME_SAMPLING),
        status=kwargs.get("status", AnalysisStatus.COMPLETED),
        params=kwargs.get("params", {"sample_rate": 1}),
        result=kwargs.get("result", {"frames": 10}),
        started_at=kwargs.get("started_at"),
        completed_at=kwargs.get("completed_at"),
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


# --- list ---


def test_list_evidence_empty(client: TestClient):
    resp = client.get("/api/v1/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["total_pages"] == 0


def test_list_evidence_returns_all(client: TestClient, case: Case):
    for i in range(3):
        upload(client, case.id, FAKE_MP4, filename=f"clip{i}.mp4")

    resp = client.get("/api/v1/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert {item["original_filename"] for item in body["items"]} == {
        "clip0.mp4",
        "clip1.mp4",
        "clip2.mp4",
    }
    assert all(item["case_number"] == "CASE-T1" for item in body["items"])


def test_list_evidence_pagination(client: TestClient, case: Case):
    for i in range(5):
        upload(client, case.id, FAKE_MP4, filename=f"clip{i}.mp4")

    resp = client.get("/api/v1/evidence", params={"page": 2, "page_size": 2})
    body = resp.json()
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert len(body["items"]) == 2


def test_list_evidence_filters_by_case(client: TestClient, case: Case, db_session: Session):
    other_case = Case(case_number="CASE-T2", title="Other", investigator_id=case.investigator_id)
    db_session.add(other_case)
    db_session.commit()

    upload(client, case.id, FAKE_MP4, filename="a.mp4")
    upload(client, other_case.id, FAKE_MP4, filename="b.mp4")

    resp = client.get("/api/v1/evidence", params={"case_id": str(case.id)})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["original_filename"] == "a.mp4"


def test_list_evidence_filters_by_status(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    upload(client, case.id, FAKE_MP4, filename="plain.mp4")
    other_id = upload(client, case.id, sample_video.read_bytes(), filename="analyzed.mp4").json()[
        "id"
    ]
    client.post(f"/api/v1/evidence/{other_id}/metadata")

    resp = client.get("/api/v1/evidence", params={"status": "metadata_extracted"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["original_filename"] == "analyzed.mp4"


def test_list_evidence_search(client: TestClient, case: Case):
    upload(client, case.id, FAKE_MP4, filename="night_incident.mp4")
    upload(client, case.id, FAKE_MP4, filename="day_incident.mp4")

    by_filename = client.get("/api/v1/evidence", params={"search": "night"})
    assert by_filename.json()["total"] == 1

    by_evidence_number = client.get("/api/v1/evidence", params={"search": "EVD-"})
    assert by_evidence_number.json()["total"] == 2

    by_case_number = client.get("/api/v1/evidence", params={"search": "CASE-T1"})
    assert by_case_number.json()["total"] == 2


def test_list_evidence_hides_deleted(client: TestClient, case: Case):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]
    client.delete(f"/api/v1/evidence/{evidence_id}")

    resp = client.get("/api/v1/evidence")
    assert resp.json()["total"] == 0

    resp_deleted = client.get("/api/v1/evidence", params={"status": "deleted"})
    assert resp_deleted.json()["total"] == 1


def test_list_evidence_invalid_page_size_422(client: TestClient):
    resp = client.get("/api/v1/evidence", params={"page_size": 1000})
    assert resp.status_code == 422


# --- detail ---


def test_evidence_detail_includes_metadata_and_analyses(
    client: TestClient, case: Case, db_session: Session, sample_video: Path
):
    evidence_id = upload(
        client, case.id, sample_video.read_bytes(), filename="detailed.mp4"
    ).json()["id"]
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    analysis = _make_analysis(db_session, uuid.UUID(evidence_id))

    resp = client.get(f"/api/v1/evidence/{evidence_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["original_filename"] == "detailed.mp4"
    assert body["video_metadata"]["width"] == 320
    assert body["video_metadata"]["height"] == 240
    assert len(body["analyses"]) == 1
    assert body["analyses"][0]["id"] == str(analysis.id)


def test_evidence_detail_unknown_404(client: TestClient):
    resp = client.get(f"/api/v1/evidence/{uuid.uuid4()}")
    assert resp.status_code == 404


# --- analysis list ---


def test_evidence_analysis_list(client: TestClient, case: Case, db_session: Session):
    evidence_id = uuid.UUID(upload(client, case.id, FAKE_MP4).json()["id"])
    first = _make_analysis(db_session, evidence_id)
    second = _make_analysis(db_session, evidence_id, analysis_type=AnalysisType.SCENE_CHANGE)

    resp = client.get(f"/api/v1/evidence/{evidence_id}/analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert {item["analysis_type"] for item in body} == {"frame_sampling", "scene_change"}
    assert {item["id"] for item in body} == {str(first.id), str(second.id)}


def test_evidence_analysis_list_empty(client: TestClient, case: Case):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]
    resp = client.get(f"/api/v1/evidence/{evidence_id}/analysis")
    assert resp.status_code == 200
    assert resp.json() == []


def test_evidence_analysis_unknown_404(client: TestClient):
    resp = client.get(f"/api/v1/evidence/{uuid.uuid4()}/analysis")
    assert resp.status_code == 404


# --- delete ---


def test_delete_evidence_soft_deletes(client: TestClient, case: Case, db_session: Session):
    evidence_id = uuid.UUID(upload(client, case.id, FAKE_MP4).json()["id"])

    resp = client.delete(f"/api/v1/evidence/{evidence_id}")
    assert resp.status_code == 204

    evidence = db_session.get(Evidence, evidence_id)
    assert evidence is not None
    assert evidence.status.value == "deleted"
    assert Path(evidence.storage_path).exists()

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "evidence.delete")
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.entity_id == evidence_id


def test_delete_evidence_twice_is_idempotent(client: TestClient, case: Case):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]
    assert client.delete(f"/api/v1/evidence/{evidence_id}").status_code == 204
    assert client.delete(f"/api/v1/evidence/{evidence_id}").status_code == 204


def test_delete_evidence_unknown_404(client: TestClient):
    resp = client.delete(f"/api/v1/evidence/{uuid.uuid4()}")
    assert resp.status_code == 404
