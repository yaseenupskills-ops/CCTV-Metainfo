import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, AnalysisType, EvidenceStatus
from app.models import Analysis, AuditLog, Case, Evidence
from tests.helpers import FAKE_MP4, upload


def _upload_sample(client: TestClient, case: Case, sample_video: Path) -> str:
    resp = upload(client, case.id, sample_video.read_bytes(), filename="sample.mp4")
    assert resp.status_code == 201
    return resp.json()["id"]


def test_analyze_frame_sampling_completes(
    client: TestClient, case: Case, sample_video: Path, db_session: Session
):
    evidence_id = _upload_sample(client, case, sample_video)
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["analysis_type"] == "frame_sampling"
    assert body["status"] == "completed"
    assert body["params"]["sampling_rate"] == 1
    assert body["result"]["sampling_rate"] == 1
    assert body["result"]["frames_sampled"] >= 1
    assert body["started_at"] is not None
    assert body["completed_at"] is not None

    evidence = db_session.get(Evidence, uuid.UUID(evidence_id))
    assert evidence is not None
    assert evidence.status == EvidenceStatus.ANALYZED


def test_analyze_records_status_transitions(
    client: TestClient, case: Case, sample_video: Path, db_session: Session
):
    evidence_id = _upload_sample(client, case, sample_video)
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    )
    assert resp.status_code == 200

    analysis = db_session.execute(
        select(Analysis).where(Analysis.evidence_id == uuid.UUID(evidence_id))
    ).scalar_one()
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.result is not None


def test_analyze_defaults_sampling_rate(client: TestClient, case: Case, sample_video: Path):
    evidence_id = _upload_sample(client, case, sample_video)
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling"},
    )
    assert resp.status_code == 200
    assert resp.json()["params"]["sampling_rate"] == 1


def test_analyze_rejects_unsupported_sampling_rate(
    client: TestClient, case: Case, sample_video: Path
):
    evidence_id = _upload_sample(client, case, sample_video)
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 7},
    )
    assert resp.status_code == 422


def test_analyze_rejects_unsupported_type(client: TestClient, case: Case, sample_video: Path):
    evidence_id = _upload_sample(client, case, sample_video)
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "comparison", "sampling_rate": 1},
    )
    assert resp.status_code == 422


def test_analyze_scene_change_completes(
    client: TestClient, case: Case, scene_change_video_factory, db_session: Session
):
    video = scene_change_video_factory()
    evidence_id = upload(client, case.id, video.read_bytes(), filename="scene.mp4").json()["id"]
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1, "threshold": 0.5},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["analysis_type"] == "scene_change"
    assert body["status"] == "completed"
    assert body["params"]["sampling_rate"] == 1
    assert body["params"]["threshold"] == 0.5
    assert body["result"]["threshold"] == 0.5
    assert body["result"]["events"], "expected an event at the scene cut"

    evidence = db_session.get(Evidence, uuid.UUID(evidence_id))
    assert evidence is not None
    assert evidence.status == EvidenceStatus.ANALYZED


def test_analyze_scene_change_defaults_threshold(
    client: TestClient, case: Case, scene_change_video_factory
):
    video = scene_change_video_factory()
    evidence_id = upload(client, case.id, video.read_bytes(), filename="scene.mp4").json()["id"]
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["params"]["threshold"] == 0.35


def test_analyze_scene_change_rejects_bad_threshold(
    client: TestClient, case: Case, sample_video: Path
):
    evidence_id = _upload_sample(client, case, sample_video)
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1, "threshold": 0.0},
    )
    assert resp.status_code == 422


def test_analyze_unknown_evidence_404(client: TestClient):
    resp = client.post(
        f"/api/v1/evidence/{uuid.uuid4()}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    )
    assert resp.status_code == 404


def test_analyze_fails_on_corrupt_file(client: TestClient, case: Case, db_session: Session):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    )
    assert resp.status_code == 500

    # The worker writes through its own session, so drop this session's stale
    # copy of the Analysis (queued) before re-reading the persisted state.
    db_session.expire_all()
    analysis = db_session.execute(
        select(Analysis).where(Analysis.evidence_id == uuid.UUID(evidence_id))
    ).scalar_one()
    assert analysis.status == AnalysisStatus.FAILED
    assert analysis.error_message


def test_analyze_writes_audit_log(
    client: TestClient, case: Case, sample_video: Path, db_session: Session
):
    evidence_id = _upload_sample(client, case, sample_video)
    client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    )

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "evidence.analyze")
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.entity_id == uuid.UUID(evidence_id)
    assert entry.details["sampling_rate"] == 1
    assert entry.details["status"] == "completed"


# --- summary on the analyze response and the list endpoint ---------------


def test_analyze_response_includes_summary(
    client: TestClient, case: Case, sample_video: Path
):
    """The analyze response is AnalysisDetail, which now also carries summary."""
    evidence_id = _upload_sample(client, case, sample_video)
    body = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    ).json()

    assert body["summary"] == {"frames_sampled": body["result"]["frames_sampled"]}


def test_analysis_list_exposes_summary_without_the_full_result(
    client: TestClient, case: Case, sample_video: Path
):
    """The list endpoint is what the analyses table renders from.

    It must report what the run found while omitting the bulky result, which is
    what previously left the result column showing a dash for every row.
    """
    evidence_id = _upload_sample(client, case, sample_video)
    client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    )

    rows = client.get(f"/api/v1/evidence/{evidence_id}/analysis").json()
    assert rows
    row = rows[0]

    assert row["status"] == "completed"
    assert "result" not in row, "the list must stay small"
    assert row["summary"] == {"frames_sampled": row["summary"]["frames_sampled"]}
    assert row["summary"]["frames_sampled"] >= 1


def test_analysis_list_summary_matches_the_detail_result(
    client: TestClient, case: Case, sample_video: Path
):
    """A list row must agree with the full result it summarises."""
    evidence_id = _upload_sample(client, case, sample_video)
    detail = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "frame_sampling", "sampling_rate": 1},
    ).json()

    row = client.get(f"/api/v1/evidence/{evidence_id}/analysis").json()[0]

    assert row["summary"] == detail["summary"]


def test_analysis_list_summary_is_none_before_completion(
    client: TestClient, case: Case, sample_video: Path, db_session: Session
):
    evidence_id = _upload_sample(client, case, sample_video)
    db_session.add(
        Analysis(
            evidence_id=uuid.UUID(evidence_id),
            analysis_type=AnalysisType.SCENE_CHANGE,
            status=AnalysisStatus.QUEUED,
            params={"sampling_rate": 1, "threshold": 0.35},
        )
    )
    db_session.commit()

    row = client.get(f"/api/v1/evidence/{evidence_id}/analysis").json()[0]

    assert row["status"] == "queued"
    assert row["summary"] is None


def test_analysis_list_summary_counts_scene_change_events(
    client: TestClient, case: Case, sample_video: Path, db_session: Session
):
    evidence_id = _upload_sample(client, case, sample_video)
    db_session.add(
        Analysis(
            evidence_id=uuid.UUID(evidence_id),
            analysis_type=AnalysisType.SCENE_CHANGE,
            status=AnalysisStatus.COMPLETED,
            params={"sampling_rate": 1, "threshold": 0.35},
            result={"events": [{"timestamp": 1.0}, {"timestamp": 5.0}]},
        )
    )
    db_session.commit()

    row = client.get(f"/api/v1/evidence/{evidence_id}/analysis").json()[0]

    assert row["summary"] == {"events": 2}
