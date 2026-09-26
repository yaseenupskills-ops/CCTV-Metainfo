from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, AnalysisType, EvidenceStatus
from app.core.exceptions import ValidationError
from app.forensic.frames import extract_frames
from app.forensic.scene_diff import detect_scene_changes
from app.models import Analysis, Evidence
from app.services.storage_service import StorageService


def _now() -> datetime:
    return datetime.now(UTC)


def _working_copy_path(evidence: Evidence) -> str:
    return str(StorageService().create_working_copy(evidence))


def create_pending_analysis(
    db: Session,
    evidence: Evidence,
    *,
    analysis_type: AnalysisType,
    params: dict,
) -> Analysis:
    """Persist a QUEUED analysis row for a later background worker to run."""
    analysis = Analysis(
        evidence_id=evidence.id,
        analysis_type=analysis_type,
        status=AnalysisStatus.QUEUED,
        params=params,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _dispatch_runner(db: Session, analysis: Analysis) -> Callable[[], dict]:
    """Return the runnable for an analysis, bound to its stored params."""
    evidence = db.get(Evidence, analysis.evidence_id)
    if evidence is None:
        raise ValidationError("The evidence for this analysis no longer exists")

    path = _working_copy_path(evidence)
    if analysis.analysis_type is AnalysisType.FRAME_SAMPLING:
        return lambda: extract_frames(path, analysis.params["sampling_rate"])
    if analysis.analysis_type is AnalysisType.SCENE_CHANGE:
        return lambda: detect_scene_changes(
            path, analysis.params["sampling_rate"], analysis.params["threshold"]
        )
    raise ValidationError(f"analysis_type '{analysis.analysis_type.value}' is not supported yet")


def execute_pending_analysis(db: Session, analysis: Analysis) -> Analysis:
    """Run a QUEUED analysis, recording PROCESSING→COMPLETED/FAILED.

    On failure the original error is re-raised after persisting the FAILED
    state so the caller (e.g. a Celery task) surfaces a meaningful outcome
    while the analysis history stays intact.
    """
    if analysis.status is not AnalysisStatus.QUEUED:
        raise ValidationError("Only QUEUED analyses can be executed")

    analysis.status = AnalysisStatus.PROCESSING
    analysis.started_at = _now()
    db.add(analysis)
    db.commit()

    try:
        result = _dispatch_runner(db, analysis)()
    except Exception as exc:
        analysis.status = AnalysisStatus.FAILED
        analysis.completed_at = _now()
        analysis.error_message = str(exc)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        raise

    evidence = db.get(Evidence, analysis.evidence_id)
    analysis.status = AnalysisStatus.COMPLETED
    analysis.completed_at = _now()
    analysis.result = result
    if evidence is not None:
        evidence.status = EvidenceStatus.ANALYZED
        db.add(evidence)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    if analysis.analysis_type is AnalysisType.SCENE_CHANGE:
        from app.services.anomaly_service import persist_anomalies_and_score

        persist_anomalies_and_score(db, analysis)
    return analysis
