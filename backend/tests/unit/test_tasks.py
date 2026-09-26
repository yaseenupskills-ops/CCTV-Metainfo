import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, AnalysisType, EvidenceStatus, UserRole
from app.core.exceptions import ValidationError
from app.models import Analysis, Case, Evidence, User, VideoMetadata
from app.services import frame_analysis_service
from app.services.frame_analysis_service import (
    create_pending_analysis,
    execute_pending_analysis,
)
from app.workers.tasks import run_analysis_task, run_metadata_task


def _evidence(db: Session) -> Evidence:
    user = User(
        name="Analyst",
        email="analyst@test.local",
        password_hash="not-a-real-hash",
        role=UserRole.INVESTIGATOR,
    )
    db.add(user)
    db.flush()
    case = Case(case_number="CASE-W", title="Worker Test", investigator_id=user.id)
    db.add(case)
    db.flush()
    evidence = Evidence(
        case_id=case.id,
        evidence_number="EVID-W",
        original_filename="clip.mp4",
        stored_filename="clip.mp4",
        file_size=1024,
        mime_type="video/mp4",
        storage_path="/unused",
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.commit()
    return evidence


def _mock_forensics(monkeypatch, *, result=None, error=None):
    def runner(path, *args):
        if error is not None:
            raise error
        return result or {"frames_sampled": 10}

    monkeypatch.setattr(
        frame_analysis_service, "_working_copy_path", lambda evidence: "/fake/video.mp4"
    )
    monkeypatch.setattr(frame_analysis_service, "extract_frames", runner)
    monkeypatch.setattr(frame_analysis_service, "detect_scene_changes", runner)


def test_create_pending_analysis_queues_row(db_session: Session):
    evidence = _evidence(db_session)

    analysis = create_pending_analysis(
        db_session,
        evidence,
        analysis_type=AnalysisType.FRAME_SAMPLING,
        params={"sampling_rate": 1},
    )

    assert analysis.id is not None
    assert analysis.status is AnalysisStatus.QUEUED
    stored = db_session.get(Analysis, analysis.id)
    assert stored is not None
    assert stored.params == {"sampling_rate": 1}
    assert stored.started_at is None


def test_execute_pending_analysis_completes_frame_sampling(db_session: Session, monkeypatch):
    evidence = _evidence(db_session)
    analysis = create_pending_analysis(
        db_session,
        evidence,
        analysis_type=AnalysisType.FRAME_SAMPLING,
        params={"sampling_rate": 1},
    )
    _mock_forensics(monkeypatch, result={"frames_sampled": 10})

    completed = execute_pending_analysis(db_session, analysis)

    assert completed.status is AnalysisStatus.COMPLETED
    assert completed.started_at is not None
    assert completed.completed_at is not None
    assert completed.result == {"frames_sampled": 10}
    assert completed.error_message is None
    stored_evidence = db_session.get(Evidence, evidence.id)
    assert stored_evidence is not None
    assert stored_evidence.status is EvidenceStatus.ANALYZED


def test_execute_pending_analysis_records_failure_and_reraises(db_session: Session, monkeypatch):
    evidence = _evidence(db_session)
    analysis = create_pending_analysis(
        db_session,
        evidence,
        analysis_type=AnalysisType.FRAME_SAMPLING,
        params={"sampling_rate": 1},
    )
    boom = RuntimeError("ffmpeg exploded")
    _mock_forensics(monkeypatch, error=boom)

    with pytest.raises(RuntimeError, match="ffmpeg exploded"):
        execute_pending_analysis(db_session, analysis)

    stored = db_session.get(Analysis, analysis.id)
    assert stored is not None
    assert stored.status is AnalysisStatus.FAILED
    assert stored.error_message == "ffmpeg exploded"
    assert stored.completed_at is not None


def test_execute_pending_analysis_rejects_non_queued(db_session: Session):
    evidence = _evidence(db_session)
    analysis = create_pending_analysis(
        db_session,
        evidence,
        analysis_type=AnalysisType.FRAME_SAMPLING,
        params={"sampling_rate": 1},
    )
    analysis.status = AnalysisStatus.PROCESSING
    db_session.commit()

    with pytest.raises(ValidationError, match="Only QUEUED analyses"):
        execute_pending_analysis(db_session, analysis)


def test_execute_pending_analysis_runs_scene_change_and_persists_anomalies(
    db_session: Session, monkeypatch
):
    evidence = _evidence(db_session)
    analysis = create_pending_analysis(
        db_session,
        evidence,
        analysis_type=AnalysisType.SCENE_CHANGE,
        params={"sampling_rate": 1, "threshold": 0.5},
    )
    _mock_forensics(
        monkeypatch,
        result={
            "events": [{"timestamp": 1.0, "score": 0.8}],
            "threshold": 0.5,
            "sampling_rate": 1,
        },
    )

    persisted: list[int] = []

    def fake_persist(db, analysis_obj):
        persisted.append(analysis_obj.id)

    monkeypatch.setattr("app.services.anomaly_service.persist_anomalies_and_score", fake_persist)

    completed = execute_pending_analysis(db_session, analysis)

    assert completed.status is AnalysisStatus.COMPLETED
    assert persisted == [completed.id]


def test_run_analysis_task_missing_analysis_returns_missing(db_session: Session):
    result = run_analysis_task(uuid.uuid4())

    assert result["status"] == "missing"


def test_run_analysis_task_executes_queued(db_session: Session, monkeypatch):
    evidence = _evidence(db_session)
    analysis = create_pending_analysis(
        db_session,
        evidence,
        analysis_type=AnalysisType.FRAME_SAMPLING,
        params={"sampling_rate": 1},
    )
    _mock_forensics(monkeypatch, result={"frames_sampled": 10})

    result = run_analysis_task(analysis.id)

    assert result["status"] == "completed"
    assert result["analysis_id"] == str(analysis.id)
    assert result["result"] == {"frames_sampled": 10}
    db_session.expire_all()
    stored = db_session.get(Analysis, analysis.id)
    assert stored is not None
    assert stored.status is AnalysisStatus.COMPLETED


def _mock_probe(monkeypatch, *, probe=None, keyframes=None):
    def value_or_callable(value):
        return value if callable(value) else (lambda *_a, **_kw: value)

    monkeypatch.setattr(
        "app.services.metadata_service.probe_video",
        value_or_callable(
            probe or {
                "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
                "streams": [],
                "tags": {},
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.structure_service.probe_keyframes",
        value_or_callable(
            keyframes or {"frames": [{"key_frame": 1, "pts_time": "0.000000", "pict_type": "I"}]}
        ),
    )


def test_run_metadata_task_missing_evidence_returns_missing(db_session: Session):
    result = run_metadata_task(uuid.uuid4())

    assert result["status"] == "missing"


def test_run_metadata_task_completes_and_normalizes(db_session: Session, monkeypatch):
    evidence = _evidence(db_session)
    _mock_probe(
        monkeypatch,
        probe={
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "1.0", "tags": {}},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 320,
                    "height": 240,
                    "r_frame_rate": "10/1",
                    "pix_fmt": "yuv420p",
                    "nb_frames": "10",
                    "tags": {},
                }
            ],
        },
    )

    result = run_metadata_task(evidence.id)

    assert result["status"] == "completed"
    assert result["evidence_id"] == str(evidence.id)
    assert result["width"] == 320
    assert result["height"] == 240
    assert result["duration"] == 1.0

    db_session.expire_all()
    metadata = db_session.get(VideoMetadata, evidence.id)
    assert metadata is not None
    assert metadata.video_codec == "h264"
    assert metadata.container_format == "mov,mp4,m4a,3gp,3g2,mj2"
    assert metadata.frame_rate == pytest.approx(10.0)
    assert metadata.metadata_json["structure"]["keyframe_count"] == 1

    stored = db_session.get(Evidence, evidence.id)
    assert stored is not None
    assert stored.status is EvidenceStatus.METADATA_EXTRACTED


def test_run_metadata_task_propagates_probe_failure(db_session: Session, monkeypatch):
    evidence = _evidence(db_session)

    def boom(*_args, **_kwargs):
        raise RuntimeError("ffprobe exploded")

    monkeypatch.setattr("app.services.metadata_service.probe_video", boom)
    monkeypatch.setattr(
        "app.services.structure_service.probe_keyframes",
        lambda *_a, **_kw: {"frames": []},
    )

    with pytest.raises(RuntimeError, match="ffprobe exploded"):
        run_metadata_task(evidence.id)

    db_session.expire_all()
    stored = db_session.get(Evidence, evidence.id)
    assert stored is not None
    assert stored.status is EvidenceStatus.UPLOADED
