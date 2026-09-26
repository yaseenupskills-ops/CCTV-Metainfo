import base64
import re
import uuid
import zlib
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Case, Report
from tests.helpers import upload


def _pdf_text(pdf_bytes: bytes) -> str:
    """Extract display text from a ReportLab PDF without external libraries."""
    chunks: list[str] = []
    for stream in re.finditer(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        raw = stream.group(1)
        try:
            data = zlib.decompress(base64.a85decode(raw, adobe=True))
        except Exception:
            try:
                data = zlib.decompress(raw)
            except Exception:
                continue
        for text in re.finditer(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", data):
            chunk = text.group(1).replace(rb"\(", b"(").replace(rb"\)", b")")
            chunks.append(chunk.decode("latin-1", "replace"))
    return "\n".join(chunks)


def _upload(client: TestClient, case: Case, path: Path, filename: str) -> str:
    return upload(client, case.id, path.read_bytes(), filename=filename).json()["id"]


def _run_scene_change(client: TestClient, evidence_id: str) -> dict:
    resp = client.post(
        f"/api/v1/evidence/{evidence_id}/analyze",
        json={"analysis_type": "scene_change", "sampling_rate": 1, "threshold": 0.5},
    )
    assert resp.status_code == 200
    return resp.json()


def _generate(
    client: TestClient,
    *,
    case_id: uuid.UUID,
    evidence_id: str | None = None,
    comparison_id: str | None = None,
):
    body: dict = {"case_id": str(case_id)}
    if evidence_id:
        body["evidence_id"] = evidence_id
    if comparison_id:
        body["comparison_id"] = comparison_id
    return client.post("/api/v1/reports", json=body)


def test_generate_report_writes_pdf_and_audits(
    client: TestClient,
    case: Case,
    scene_change_video_factory,
    db_session: Session,
):
    evidence_id = _upload(client, case, scene_change_video_factory(), "scene.mp4")
    client.post(f"/api/v1/evidence/{evidence_id}/metadata")
    _run_scene_change(client, evidence_id)

    resp = _generate(client, case_id=case.id, evidence_id=evidence_id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["case_id"] == str(case.id)
    assert body["evidence_id"] == evidence_id
    assert body["case_number"] == case.case_number
    assert body["evidence_number"] is not None

    report = db_session.get(Report, uuid.UUID(body["id"]))
    assert report is not None
    pdf_path = Path(report.report_path)
    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"

    text = _pdf_text(pdf_path.read_bytes())
    for marker in [
        "CCTV FORENSIC ANALYSIS REPORT",
        "OBSERVED FACT",
        "AUTOMATED INTERPRETATION",
        "INVESTIGATOR CONCLUSION",
        "1. Case Information",
        "2. Evidence Information",
        "3. Integrity",
        "4. Metadata",
        "5. Video Analysis",
        "6. Frame Analysis",
        "7. Anomalies",
        "8. Timeline",
        "10. Audit Trail",
        "11. Technical Conclusion",
        "12. Disclaimer",
    ]:
        assert marker in text, f"missing PDF marker: {marker}"

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "report.create")
    ).scalar_one()
    assert report is not None
    assert entry.entity_id == report.id
    assert entry.details["evidence_id"] == evidence_id


def test_download_returns_pdf(client: TestClient, case: Case, scene_change_video_factory):
    evidence_id = _upload(client, case, scene_change_video_factory(), "scene.mp4")
    report_id = _generate(client, case_id=case.id, evidence_id=evidence_id).json()["id"]

    resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_generate_report_unknown_case_404(client: TestClient):
    resp = _generate(client, case_id=uuid.uuid4())
    assert resp.status_code == 404


def test_generate_report_unknown_evidence_404(client: TestClient, case: Case):
    resp = _generate(client, case_id=case.id, evidence_id=str(uuid.uuid4()))
    assert resp.status_code == 404


def test_generate_report_unknown_comparison_404(client: TestClient, case: Case, sample_video: Path):
    evidence_id = _upload(client, case, sample_video, "a.mp4")
    resp = _generate(
        client,
        case_id=case.id,
        evidence_id=evidence_id,
        comparison_id=str(uuid.uuid4()),
    )
    assert resp.status_code == 404


def test_generate_report_with_comparison(client: TestClient, case: Case, sample_video: Path):
    content = sample_video.read_bytes()
    original_id = upload(client, case.id, content, "o.mp4").json()["id"]
    suspected_id = upload(client, case.id, content, "s.mp4").json()["id"]
    comparison = client.post(
        "/api/v1/comparisons",
        json={
            "original_evidence_id": original_id,
            "suspected_evidence_id": suspected_id,
        },
    )
    assert comparison.status_code == 201

    resp = _generate(client, case_id=case.id, comparison_id=comparison.json()["id"])
    assert resp.status_code == 201
    assert resp.json()["comparison_id"] == comparison.json()["id"]


def test_report_without_evidence_generates_case_only_pdf(client: TestClient, case: Case):
    resp = _generate(client, case_id=case.id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["evidence_id"] is None
    assert body["case_number"] == case.case_number


def test_list_reports_paginated_and_filtered(client: TestClient, case: Case):
    ids = [_generate(client, case_id=case.id).json()["id"] for _ in range(3)]

    resp = client.get("/api/v1/reports", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["case_number"] == case.case_number

    page2 = client.get("/api/v1/reports", params={"page": 2, "page_size": 2}).json()
    assert len(page2["items"]) == 1

    filtered = client.get("/api/v1/reports", params={"case_id": str(case.id)}).json()
    assert filtered["total"] == 3
    assert all(item["id"] in ids for item in filtered["items"])


def test_get_report_unknown_404(client: TestClient):
    resp = client.get(f"/api/v1/reports/{uuid.uuid4()}")
    assert resp.status_code == 404
