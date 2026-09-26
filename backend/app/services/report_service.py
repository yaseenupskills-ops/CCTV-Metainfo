"""PDF forensic report generation with ReportLab.

Generates a professional, print-ready forensic report that clearly separates
OBSERVED FACTS (measurements, hashes, audit trail) from AUTOMATED
INTERPRETATIONS (frame differences, anomaly indicators, comparison verdicts)
and reserves space for INVESTIGATOR CONCLUSIONS. The PDF never states that
tampering occurred — indicators are labeled for expert review.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models import AuditLog, Case, Comparison, Evidence, Report
from app.services.anomaly_service import get_anomaly_score
from app.services.comparison_service import get_comparison_or_404
from app.services.evidence_service import get_case_or_404, get_evidence_detail
from app.services.timeline_service import build_timeline
from app.utils.file_utils import human_size

_ACCENT = colors.HexColor("#1e3a8a")
_FACT = colors.HexColor("#047857")  # green — observed fact
_INTERPRETATION = colors.HexColor("#b45309")  # amber — automated interpretation
_CONCLUSION = colors.HexColor("#1d4ed8")  # blue — investigator conclusion
_MUTED = colors.HexColor("#6b7280")


class _Styles:
    """Central set of paragraph styles used across the report."""

    def __init__(self) -> None:
        base = getSampleStyleSheet()
        self.title = ParagraphStyle("Title", parent=base["Title"], textColor=_ACCENT, fontSize=24)
        self.subtitle = ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            textColor=_MUTED,
            fontSize=12,
            alignment=TA_CENTER,
        )
        self.h1 = ParagraphStyle(
            "H1",
            parent=base["Heading2"],
            textColor=_ACCENT,
            fontSize=14,
            spaceBefore=14,
            spaceAfter=6,
        )
        self.h2 = ParagraphStyle(
            "H2",
            parent=base["Heading3"],
            textColor=colors.HexColor("#111827"),
            fontSize=11,
            spaceBefore=10,
            spaceAfter=4,
        )
        self.body = ParagraphStyle("Body", parent=base["Normal"], fontSize=9.5, leading=13)
        self.small = ParagraphStyle("Small", parent=base["Normal"], fontSize=8.5, leading=11)
        self.muted = ParagraphStyle("Muted", parent=self.small, textColor=_MUTED)
        self.tag = ParagraphStyle("Tag", parent=self.small, fontSize=7.5, leading=9)


def _tag(label: str, color: colors.Color, style: _Styles) -> Paragraph:
    html_color = (
        f"#{round(color.red * 255):02x}{round(color.green * 255):02x}{round(color.blue * 255):02x}"
    )
    return Paragraph(
        f'<font color="{html_color}">{label}</font>',
        ParagraphStyle(
            "Tagged",
            parent=style.tag,
            borderColor=color,
            borderWidth=0.7,
            borderPadding=3,
            textColor=color,
        ),
    )


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return _fmt_dt(value)
    return str(value)


def _kv_table(rows: Sequence[tuple[str, object]], styles: _Styles) -> Table:
    """Render a label/value table with alternating row shading."""
    data = [
        [Paragraph(f"<b>{label}</b>", styles.small), Paragraph(_fmt(value), styles.small)]
        for label, value in rows
    ]
    table = Table(data, colWidths=[6.0 * cm, 9.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _section_header(title: str, tag_label: str, tag_color: colors.Color, styles: _Styles) -> list:
    return [
        Spacer(1, 4),
        Paragraph(title, styles.h1),
        _tag(tag_label, tag_color, styles),
        Spacer(1, 4),
    ]


def _build_cover(styles: _Styles, *, report_id: uuid.UUID, case: Case, generated_by: str) -> list:
    return [
        Spacer(1, 4 * cm),
        Paragraph("CCTV FORENSIC ANALYSIS REPORT", styles.title),
        Spacer(1, 0.4 * cm),
        Paragraph("Technical examination of digital video evidence", styles.subtitle),
        Spacer(1, 2 * cm),
        _kv_table(
            [
                ("Report ID", str(report_id)),
                ("Case", f"{case.case_number} — {case.title}"),
                ("Generated by", generated_by),
                ("Generated at", _fmt_dt(datetime.now(UTC))),
            ],
            styles,
        ),
        Spacer(1, 1 * cm),
        Paragraph(
            "This report separates OBSERVED FACTS from AUTOMATED INTERPRETATIONS. "
            "Automated indicators are signals for expert review — they are not a "
            "finding of tampering.",
            styles.body,
        ),
    ]


def _build_case_info(styles: _Styles, case: Case) -> list:
    rows = [
        ("Case number", case.case_number),
        ("Title", case.title),
        ("Status", case.status.value if hasattr(case.status, "value") else str(case.status)),
        ("Description", case.description or "—"),
        ("Created at", _fmt_dt(case.created_at)),
    ]
    investigator = case.investigator
    if investigator:
        rows.append(("Investigator", f"{investigator.name} ({investigator.email})"))
    return _section_header("1. Case Information", "OBSERVED FACT", _FACT, styles) + [
        _kv_table(rows, styles)
    ]


def _build_evidence_info(styles: _Styles, evidence: Evidence) -> list:
    rows = [
        ("Evidence number", evidence.evidence_number),
        ("Original filename", evidence.original_filename),
        ("MIME type", evidence.mime_type),
        ("File size", human_size(evidence.file_size)),
        (
            "Status",
            evidence.status.value if hasattr(evidence.status, "value") else str(evidence.status),
        ),
        ("Uploaded at", _fmt_dt(evidence.uploaded_at)),
    ]
    return _section_header("2. Evidence Information", "OBSERVED FACT", _FACT, styles) + [
        _kv_table(rows, styles)
    ]


def _build_integrity(styles: _Styles, evidence: Evidence) -> list:
    rows = [
        ("SHA-256", evidence.sha256 or "—"),
        ("SHA-512", evidence.sha512 or "—"),
        ("Calculated at", _fmt_dt(evidence.hash_calculated_at)),
    ]
    return _section_header("3. Integrity", "OBSERVED FACT", _FACT, styles) + [
        _kv_table(rows, styles)
    ]


def _build_metadata(styles: _Styles, evidence: Evidence) -> list:
    meta = evidence.video_metadata
    if meta is None:
        return _section_header("4. Metadata", "OBSERVED FACT", _FACT, styles) + [
            Paragraph("No metadata has been extracted for this evidence.", styles.body)
        ]
    rows = [
        ("Container format", meta.container_format),
        ("Duration", f"{meta.duration:g} s" if meta.duration is not None else None),
        ("Resolution", f"{meta.width} × {meta.height}" if meta.width and meta.height else None),
        ("Frame rate", f"{meta.frame_rate:g} fps" if meta.frame_rate is not None else None),
        ("Frame count", meta.frame_count),
        ("Video codec", meta.video_codec),
        ("Audio codec", meta.audio_codec),
        ("Pixel format", meta.pixel_format),
        ("Bitrate", f"{meta.bitrate:,} bit/s" if meta.bitrate is not None else None),
        ("Stream count", meta.stream_count),
        ("Creation time", _fmt_dt(meta.creation_time)),
        ("Encoder", meta.encoder),
    ]
    return _section_header("4. Metadata", "OBSERVED FACT", _FACT, styles) + [
        _kv_table(rows, styles)
    ]


def _build_video_analysis(styles: _Styles, evidence: Evidence) -> list:
    flowables = _section_header("5. Video Analysis", "OBSERVED FACT", _FACT, styles)
    if not evidence.analyses:
        flowables.append(Paragraph("No analyses have been run on this evidence.", styles.body))
        return flowables
    for analysis in evidence.analyses:
        status = (
            analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status)
        )
        error = f" — {analysis.error_message}" if analysis.error_message else ""
        flowables.append(
            Paragraph(
                f"<b>{analysis.analysis_type}</b> ({status}){error}",
                styles.h2,
            )
        )
        flowables.append(
            Paragraph(
                f"Params: {analysis.params or {}} | Started: {_fmt_dt(analysis.started_at)} | "
                f"Completed: {_fmt_dt(analysis.completed_at)}",
                styles.muted,
            )
        )
    return flowables


def _build_frame_analysis(styles: _Styles, evidence: Evidence) -> list:
    flowables = _section_header(
        "6. Frame Analysis", "AUTOMATED INTERPRETATION", _INTERPRETATION, styles
    )
    sampling = None
    for analysis in evidence.analyses:
        if analysis.analysis_type.value == "frame_sampling" and analysis.result:
            sampling = analysis.result
    if sampling is None:
        flowables.append(Paragraph("No frame-sampling result available.", styles.body))
        return flowables
    rows = [
        (
            "Sampling rate",
            f"{sampling.get('sampling_rate')} fps" if sampling.get("sampling_rate") else "—",
        ),
        ("Frames sampled", sampling.get("frames_sampled")),
    ]
    frames = sampling.get("frames", [])
    if frames:
        first = frames[0].get("timestamp")
        last = frames[-1].get("timestamp")
        rows.append(("Frame span", f"{first}s — {last}s"))
    flowables.append(_kv_table(rows, styles))
    return flowables


def _build_anomalies(styles: _Styles, evidence: Evidence, anomaly_score: dict) -> list:
    flowables = _section_header("7. Anomalies", "AUTOMATED INTERPRETATION", _INTERPRETATION, styles)
    events = _scene_change_events(evidence)
    if not events:
        flowables.append(Paragraph("No frame-difference anomalies were recorded.", styles.body))
        return flowables
    rows = [
        (
            "Timestamp",
            "Severity",
            "Detection",
            "Diff score",
            "Frames",
        ),
    ]
    for event in events:
        rows.append(
            (
                f"{float(event.get('timestamp', 0)):g} s",
                str(event.get("severity", "—")),
                str(event.get("detection_method", "—")),
                f"{float(event.get('diff_score', 0)):.4f}",
                f"{event.get('prev_frame', '?')} → {event.get('current_frame', '?')}",
            )
        )
    table = Table(
        [[Paragraph(cell, styles.small) for cell in row] for row in rows],
        colWidths=[2.2 * cm, 2.2 * cm, 3.6 * cm, 2.4 * cm, 3.1 * cm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    flowables.append(table)
    if anomaly_score.get("score") is not None:
        flowables.append(
            Paragraph(
                f"Anomaly Indicator Score: {anomaly_score['score']}/100 "
                f"({anomaly_score.get('category', '—')}). "
                "An indicator, not a probability of tampering.",
                styles.body,
            )
        )
    return flowables


def _build_timeline(db: Session, styles: _Styles, evidence: Evidence) -> list:
    flowables = _section_header("8. Timeline", "AUTOMATED INTERPRETATION", _INTERPRETATION, styles)
    timeline = build_timeline(db, evidence)
    segments = timeline.segments
    events = timeline.events
    if not segments:
        flowables.append(Paragraph("No timeline data available.", styles.body))
        return flowables
    flowables.append(
        Paragraph(
            f"{len(segments)} segment(s), {len(events)} potential anomaly marker(s).",
            styles.body,
        )
    )
    for event in events:
        flowables.append(
            Paragraph(
                f"<b>{float(event.timestamp):g} s</b> — severity {event.severity}, "
                f"diff score {float(event.diff_score):.4f}, frames "
                f"{_fmt(event.prev_frame)} → {_fmt(event.current_frame)}",
                styles.small,
            )
        )
    return flowables


def _build_comparison(styles: _Styles, comparison: Comparison) -> list:
    flowables = _section_header(
        "9. Comparison", "AUTOMATED INTERPRETATION", _INTERPRETATION, styles
    )
    result = comparison.result
    summary = result.get("summary", {})
    flowables.append(
        Paragraph(
            f"Compared against reference evidence. Identical: <b>{summary.get('identical')}</b> "
            f"| Matches: {summary.get('matches')} | Differences: {summary.get('differences')} | "
            f"Not available: {summary.get('not_available')}.",
            styles.body,
        )
    )
    fields = result.get("fields", [])
    if not fields:
        flowables.append(Paragraph("No comparison fields recorded.", styles.body))
        return flowables
    rows = [("Property", "Verdict", "Reference", "Suspected", "Note")]
    for field in fields:
        rows.append(
            (
                str(field.get("label", field.get("field", ""))),
                str(field.get("status", "—")),
                _fmt(field.get("original")),
                _fmt(field.get("suspected")),
                str(field.get("note") or "—"),
            )
        )
    table = Table(
        [[Paragraph(cell, styles.small) for cell in row] for row in rows],
        colWidths=[3.2 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 4.5 * cm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    flowables.append(table)
    return flowables


def _build_audit_trail(styles: _Styles, audit_entries: list[AuditLog]) -> list:
    flowables = _section_header("10. Audit Trail", "OBSERVED FACT", _FACT, styles)
    if not audit_entries:
        flowables.append(Paragraph("No audit entries recorded for this evidence.", styles.body))
        return flowables
    rows = [("Timestamp", "Action", "Details")]
    for entry in audit_entries:
        rows.append(
            (
                _fmt_dt(entry.timestamp),
                entry.action,
                _fmt(entry.details)[:120],
            )
        )
    table = Table(
        [[Paragraph(cell, styles.small) for cell in row] for row in rows],
        colWidths=[3.6 * cm, 3.6 * cm, 8.3 * cm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    flowables.append(table)
    return flowables


def _build_technical_conclusion(styles: _Styles, anomaly_score: dict) -> list:
    flowables = _section_header(
        "11. Technical Conclusion", "AUTOMATED INTERPRETATION", _INTERPRETATION, styles
    ) + [
        Paragraph(
            "The following is an automated interpretation of the technical indicators. "
            "It does not constitute a finding that the evidence was altered.",
            styles.body,
        ),
    ]
    if anomaly_score.get("score") is not None:
        flowables.append(
            Paragraph(
                f"Anomaly Indicator Score: <b>{anomaly_score['score']}/100</b> "
                f"({anomaly_score.get('category', '—')}).",
                styles.h2,
            )
        )
        for factor in anomaly_score.get("factors", []):
            flowables.append(
                Paragraph(
                    f"• <b>{factor.get('label')}</b> — "
                    f"{factor.get('points')}/{factor.get('max_points')} points. "
                    f"{factor.get('reason')}",
                    styles.small,
                )
            )
    else:
        flowables.append(
            Paragraph(
                "No scene-change analysis available to derive an indicator score.",
                styles.body,
            )
        )
    flowables.append(Spacer(1, 0.5 * cm))
    flowables.append(_tag("INVESTIGATOR CONCLUSION", _CONCLUSION, styles))
    flowables.append(
        Paragraph(
            "Reserved for the investigating officer's conclusion. "
            "This section is intentionally blank in auto-generated reports.",
            styles.body,
        )
    )
    return flowables


def _build_disclaimer(styles: _Styles) -> list:
    return [
        PageBreak(),
        *_section_header("12. Disclaimer", "OBSERVED FACT", _FACT, styles),
        Paragraph(
            "This report was generated automatically by the CCTV Forensic Analyzer. "
            "Automated analyses are indicators, not proof of tampering. Technical "
            "findings must be reviewed by a qualified forensic examiner. This "
            "report does not constitute legal advice or an expert opinion.",
            styles.body,
        ),
    ]


def _scene_change_events(evidence: Evidence) -> list[dict]:
    for analysis in evidence.analyses:
        if analysis.analysis_type.value == "scene_change" and analysis.result:
            return list(analysis.result.get("events", []))
    return []


def _audit_entries_for_evidence(db: Session, evidence_id: uuid.UUID) -> list[AuditLog]:
    return list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == "evidence", AuditLog.entity_id == evidence_id)
            .order_by(AuditLog.timestamp.asc())
        )
        .scalars()
        .all()
    )


def generate_report(
    db: Session,
    *,
    case_id: uuid.UUID,
    evidence_id: uuid.UUID | None = None,
    comparison_id: uuid.UUID | None = None,
    generated_by: uuid.UUID,
) -> Report:
    """Generate a forensic PDF report and persist the report record.

    Gathers case, evidence, analysis, timeline, anomaly-score, comparison and
    audit data into a deterministic PDF stored under `storage/reports/`.
    """
    case = get_case_or_404(db, case_id)
    evidence = get_evidence_detail(db, evidence_id) if evidence_id else None
    comparison = get_comparison_or_404(db, comparison_id) if comparison_id else None
    anomaly_score = get_anomaly_score(db, evidence.id) if evidence else {}
    audit_entries = _audit_entries_for_evidence(db, evidence.id) if evidence else []

    report = Report(
        id=uuid.uuid4(),
        case_id=case.id,
        evidence_id=evidence.id if evidence else None,
        comparison_id=comparison.id if comparison else None,
        generated_by=generated_by,
    )
    report_path = settings.storage_reports_dir / f"{report.id}.pdf"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.report_path = str(report_path)
    db.add(report)
    db.flush()

    generated_by_user = report.generated_by_user
    generated_by_name = generated_by_user.name if generated_by_user else str(generated_by)

    styles = _Styles()
    story: list = _build_cover(
        styles, report_id=report.id, case=case, generated_by=generated_by_name
    )
    story.append(PageBreak())
    story.extend(_build_case_info(styles, case))
    if evidence:
        story.extend(_build_evidence_info(styles, evidence))
        story.extend(_build_integrity(styles, evidence))
        story.extend(_build_metadata(styles, evidence))
        story.extend(_build_video_analysis(styles, evidence))
        story.extend(_build_frame_analysis(styles, evidence))
        story.extend(_build_anomalies(styles, evidence, anomaly_score))
        story.extend(_build_timeline(db, styles, evidence))
    if comparison:
        story.extend(_build_comparison(styles, comparison))
    if evidence:
        story.extend(_build_audit_trail(styles, audit_entries))
        story.extend(_build_technical_conclusion(styles, anomaly_score))
    story.extend(_build_disclaimer(styles))

    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Forensic Report {report.id}",
        author="CCTV Forensic Analyzer",
    )
    doc.build(story)

    db.commit()
    db.refresh(report)
    return report


def get_report_or_404(db: Session, report_id: uuid.UUID) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found")
    return report
