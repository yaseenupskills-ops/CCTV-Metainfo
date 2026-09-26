import uuid

from fastapi import APIRouter, Request

from app.api.deps import DbSession, StaffUser
from app.core.config import settings
from app.core.enums import AnalysisType
from app.core.exceptions import ValidationError
from app.schemas.analysis import AnalysisDetail, AnalysisStart
from app.services.audit_service import AuditService
from app.services.evidence_service import get_evidence_or_404
from app.services.frame_analysis_service import create_pending_analysis
from app.workers.tasks import run_analysis_task

router = APIRouter(prefix="/evidence", tags=["analysis"])


@router.post("/{evidence_id}/analyze", response_model=AnalysisDetail)
def analyze_evidence(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    evidence_id: uuid.UUID,
    body: AnalysisStart,
) -> AnalysisDetail:
    """Queue an analysis on an evidence for the background worker.

    Supported types: `frame_sampling` and `scene_change`. The sampling rate
    defaults to the configured value and must be one of the allowed rates.
    `scene_change` accepts an optional `threshold` (defaults to the configured
    value) controlling what counts as a significant frame difference.
    """
    if body.analysis_type not in (
        AnalysisType.FRAME_SAMPLING,
        AnalysisType.SCENE_CHANGE,
    ):
        raise ValidationError(f"analysis_type '{body.analysis_type.value}' is not supported yet")

    sampling_rate = body.sampling_rate or settings.default_frame_sampling_rate
    if sampling_rate not in settings.frame_sampling_rates:
        allowed = ", ".join(str(rate) for rate in settings.frame_sampling_rates)
        raise ValidationError(f"sampling_rate must be one of: {allowed}")

    threshold: float | None = body.threshold
    if body.analysis_type is AnalysisType.SCENE_CHANGE:
        threshold = threshold if threshold is not None else settings.scene_diff_threshold
        if not 0.0 < threshold <= 1.0:
            raise ValidationError("threshold must be between 0 and 1")

    evidence = get_evidence_or_404(db, evidence_id)
    if body.analysis_type is AnalysisType.SCENE_CHANGE:
        params = {
            "sampling_rate": sampling_rate,
            "threshold": threshold or settings.scene_diff_threshold,
        }
    else:
        params = {"sampling_rate": sampling_rate}

    analysis = create_pending_analysis(
        db, evidence, analysis_type=body.analysis_type, params=params
    )
    run_analysis_task.delay(analysis.id)
    db.refresh(analysis)

    AuditService.record(
        db,
        action="evidence.analyze",
        entity_type="evidence",
        entity_id=evidence.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={
            "analysis_type": analysis.analysis_type.value,
            "sampling_rate": sampling_rate,
            "status": analysis.status.value,
            "result_summary": _result_summary(analysis),
        },
    )
    return AnalysisDetail.model_validate(analysis)


def _result_summary(analysis) -> dict:
    """Extract a compact summary from an analysis result for the audit log."""
    result = analysis.result or {}
    if analysis.analysis_type is AnalysisType.SCENE_CHANGE:
        return {"events": len(result.get("events", []))}
    return {"frames_sampled": result.get("frames_sampled")}
