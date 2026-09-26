import uuid

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Analysis, Evidence
from app.services.frame_analysis_service import execute_pending_analysis
from app.services.metadata_service import extract_and_store_metadata
from app.services.structure_service import extract_structure
from app.workers.celery_app import celery_app

_session_factory = SessionLocal


@celery_app.task(name="app.workers.tasks.run_analysis")
def run_analysis_task(analysis_id: uuid.UUID) -> dict:
    """Execute a QUEUED analysis in the background and report its outcome.

    Returns a summary dict; execution errors are re-raised so eager-mode
    callers (e.g. tests) observe the same failure as the API would.
    """
    db: Session = _session_factory()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            return {"status": "missing", "analysis_id": str(analysis_id)}
        analysis = execute_pending_analysis(db, analysis)
        return {
            "status": analysis.status.value,
            "analysis_id": str(analysis.id),
            "result": analysis.result,
        }
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_metadata")
def run_metadata_task(evidence_id: uuid.UUID) -> dict:
    """Extract video metadata and stream structure for an evidence in the background.

    Runs ffprobe against the stored original, persists normalized fields plus
    the raw probe JSON (with a derived `structure` section), and flips the
    evidence status to ``metadata_extracted``.
    """
    db: Session = _session_factory()
    try:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            return {"status": "missing", "evidence_id": str(evidence_id)}
        metadata = extract_and_store_metadata(db, evidence)
        metadata.metadata_json = {
            **metadata.metadata_json,
            "structure": extract_structure(evidence),
        }
        db.commit()
        db.refresh(metadata)
        return {
            "status": "completed",
            "evidence_id": str(evidence_id),
            "container_format": metadata.container_format,
            "duration": metadata.duration,
            "width": metadata.width,
            "height": metadata.height,
            "frame_rate": metadata.frame_rate,
        }
    finally:
        db.close()
