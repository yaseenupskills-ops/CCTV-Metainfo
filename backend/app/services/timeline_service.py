"""Timeline reconstruction for an evidence.

Builds an ordered series of normal segments and anomaly markers from the most
recent scene-change analysis result. Anomalies are zero-width markers at their
video timestamp; normal segments tile the duration between them. The endpoint
never claims tampering — markers are labeled "Potential anomaly" events for
expert interpretation.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisStatus, AnalysisType
from app.models import Analysis, Evidence
from app.schemas.timeline import TimelineEvent, TimelineResponse, TimelineSegment


def _most_recent_scene_change(db: Session, evidence_id: uuid.UUID) -> Analysis | None:
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


def build_timeline(db: Session, evidence: Evidence) -> TimelineResponse:
    """Build the timeline response for an evidence from stored analyses."""
    duration = evidence.video_metadata.duration if evidence.video_metadata else None
    analysis = _most_recent_scene_change(db, evidence.id)

    if analysis is None:
        return TimelineResponse(
            evidence_id=evidence.id,
            duration=duration,
            analysis_id=None,
            analysis_status=None,
            segments=[],
            events=[],
        )

    events: list[TimelineEvent] = []
    if analysis.status is AnalysisStatus.COMPLETED and analysis.result:
        for event in analysis.result.get("events", []):
            events.append(
                TimelineEvent(
                    timestamp=float(event.get("timestamp", 0.0)),
                    severity=str(event.get("severity", "low")),
                    detection_method=str(event.get("detection_method", "frame_difference")),
                    diff_score=float(event.get("diff_score", 0.0)),
                    prev_frame=_int_or_none(event.get("prev_frame")),
                    current_frame=_int_or_none(event.get("current_frame")),
                    metrics=event.get("metrics", {}),
                    analysis_id=analysis.id,
                    analysis_type=analysis.analysis_type,
                )
            )

    events.sort(key=lambda e: e.timestamp)
    segments = _build_segments(events, duration)

    return TimelineResponse(
        evidence_id=evidence.id,
        duration=duration,
        analysis_id=analysis.id,
        analysis_status=analysis.status,
        segments=segments,
        events=events,
    )


def _build_segments(events: list[TimelineEvent], duration: float | None) -> list[TimelineSegment]:
    segments: list[TimelineSegment] = []
    cursor = 0.0
    for index, event in enumerate(events):
        if event.timestamp > cursor:
            segments.append(TimelineSegment(kind="normal", start=cursor, end=event.timestamp))
        segments.append(
            TimelineSegment(
                kind="anomaly",
                start=event.timestamp,
                end=event.timestamp,
                severity=event.severity,
                event_index=index,
            )
        )
        cursor = max(cursor, event.timestamp)

    if duration is not None and cursor < duration:
        segments.append(TimelineSegment(kind="normal", start=cursor, end=duration))

    if not segments:
        segments.append(TimelineSegment(kind="normal", start=0.0, end=duration or 0.0))
    return segments


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
