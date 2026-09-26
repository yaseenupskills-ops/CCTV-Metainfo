"""Anomaly persistence and anomaly indicator scoring.

Persists one Anomaly row per scene-change event and attaches a deterministic,
explainable indicator score to the scene-change analysis result. The score is
recomputed whenever a comparison is created so duration/encoding deviations
against a reference are reflected without stale data.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisType, ComparisonFieldStatus, Severity
from app.forensic.scoring import (
    ScoringInputs,
    score_anomaly_indicators,
)
from app.models import Analysis, Anomaly, Comparison, Evidence

_DURATION_MISMATCH_TOLERANCE = 0.10


def _now() -> datetime:
    return datetime.now(UTC)


def _latest_scene_change(db: Session, evidence_id: uuid.UUID) -> Analysis | None:
    return (
        db.execute(
            select(Analysis)
            .where(
                Analysis.evidence_id == evidence_id,
                Analysis.analysis_type == AnalysisType.SCENE_CHANGE,
            )
            .order_by(
                Analysis.started_at.desc().nulls_last(),
                Analysis.completed_at.desc().nulls_last(),
                Analysis.id.desc(),
            )
        )
        .scalars()
        .first()
    )


def _severity_from_value(value: object) -> Severity:
    if isinstance(value, Severity):
        return value
    try:
        return Severity(str(value))
    except ValueError:
        return Severity.MEDIUM


def populate_anomalies(db: Session, analysis: Analysis) -> None:
    """Persist one Anomaly row per scene-change event (idempotent)."""
    if analysis.analysis_type is not AnalysisType.SCENE_CHANGE or not analysis.result:
        return

    already_populated = (
        db.execute(select(Anomaly.id).where(Anomaly.analysis_id == analysis.id)).scalars().first()
        is not None
    )
    if already_populated:
        return

    for event in analysis.result.get("events", []):
        timestamp = event.get("timestamp")
        diff_score = event.get("diff_score")
        db.add(
            Anomaly(
                analysis_id=analysis.id,
                timestamp=float(timestamp) if timestamp is not None else None,
                anomaly_type="scene_change",
                severity=_severity_from_value(event.get("severity")),
                confidence=float(diff_score) if diff_score is not None else None,
                description=(
                    f"Potential anomaly: frame difference between frame "
                    f"{event.get('prev_frame', '?')} and {event.get('current_frame', '?')}"
                ),
                evidence_data=dict(event),
            )
        )
    db.commit()


def _latest_comparison_for(db: Session, evidence_id: uuid.UUID) -> Comparison | None:
    return (
        db.execute(
            select(Comparison)
            .where(
                (Comparison.original_evidence_id == evidence_id)
                | (Comparison.suspected_evidence_id == evidence_id)
            )
            .order_by(Comparison.created_at.desc())
        )
        .scalars()
        .first()
    )


def _comparison_signals(comparison: Comparison | None) -> tuple[float, bool]:
    """Extract (duration_deviation, encoding_differs) from a comparison result."""
    if comparison is None:
        return 0.0, False

    fields = {field["field"]: field for field in comparison.result.get("fields", [])}
    deviation = 0.0
    duration = fields.get("duration")
    if duration and duration.get("status") is not ComparisonFieldStatus.NOT_AVAILABLE:
        original = duration.get("original")
        suspected = duration.get("suspected")
        if (
            isinstance(original, (int, float))
            and isinstance(suspected, (int, float))
            and original > 0
        ):
            deviation = abs(original - suspected) / original

    encoding_differs = any(
        field and fields.get(field, {}).get("status") is ComparisonFieldStatus.DIFFERENCE
        for field in ("video_codec", "audio_codec", "pixel_format", "encoder")
    )
    return deviation, encoding_differs


def _metadata_inconsistent(evidence: Evidence) -> bool:
    metadata = evidence.video_metadata
    if metadata is None:
        return False
    duration, frame_rate, frame_count = (
        metadata.duration,
        metadata.frame_rate,
        metadata.frame_count,
    )
    if duration and frame_rate and frame_count:
        expected = duration * frame_rate
        if expected > 0 and abs(frame_count - expected) / expected > _DURATION_MISMATCH_TOLERANCE:
            return True
    return False


def _build_scoring_inputs(db: Session, evidence: Evidence, events: list[dict]) -> ScoringInputs:
    comparison = _latest_comparison_for(db, evidence.id)
    duration_deviation, encoding_differs = _comparison_signals(comparison)
    return ScoringInputs(
        metadata_inconsistent=_metadata_inconsistent(evidence),
        duration_deviation=duration_deviation,
        encoding_differs=encoding_differs,
        discontinuities=sum(1 for event in events if float(event.get("diff_score", 0.0)) >= 0.9),
        event_timestamps=tuple(
            float(event["timestamp"]) for event in events if "timestamp" in event
        ),
    )


def persist_anomalies_and_score(db: Session, analysis: Analysis) -> None:
    """Populate Anomaly rows and attach the indicator score to the analysis result."""
    if analysis.analysis_type is not AnalysisType.SCENE_CHANGE or not analysis.result:
        return

    populate_anomalies(db, analysis)

    evidence = db.get(Evidence, analysis.evidence_id)
    if evidence is None:
        return
    score = score_anomaly_indicators(
        _build_scoring_inputs(db, evidence, analysis.result.get("events", []))
    )
    analysis.result = {
        **analysis.result,
        "anomaly_score": {
            **score.to_dict(),
            "computed_at": _now().isoformat(),
        },
    }
    db.add(analysis)
    db.commit()
    db.refresh(analysis)


def recompute_scores_for_comparison(db: Session, comparison: Comparison) -> None:
    """Refresh persisted anomaly scores that involve either compared evidence."""
    for evidence_id in (
        comparison.original_evidence_id,
        comparison.suspected_evidence_id,
    ):
        analysis = _latest_scene_change(db, evidence_id)
        if analysis is not None and analysis.result:
            persist_anomalies_and_score(db, analysis)


def get_anomaly_score(db: Session, evidence_id: uuid.UUID) -> dict:
    """Return the persisted indicator score for the most recent scene-change analysis.

    Falls back to a fresh on-demand computation when an older analysis predates
    score persistence so the endpoint never returns an empty score.
    """
    analysis = _latest_scene_change(db, evidence_id)
    if analysis is None or analysis.result is None:
        return {
            "analysis_id": None,
            "score": None,
            "category": None,
            "factors": [],
            "computed_at": None,
        }

    payload = analysis.result.get("anomaly_score")
    if payload is None:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            return {
                "analysis_id": analysis.id,
                "score": None,
                "category": None,
                "factors": [],
                "computed_at": None,
            }
        score = score_anomaly_indicators(
            _build_scoring_inputs(db, evidence, analysis.result.get("events", []))
        )
        payload = {**score.to_dict(), "computed_at": None}
    return {"analysis_id": analysis.id, **payload}
