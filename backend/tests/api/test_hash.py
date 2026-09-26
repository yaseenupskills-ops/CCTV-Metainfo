import hashlib
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Case, Evidence
from tests.helpers import FAKE_MP4, upload


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha512(content: bytes) -> str:
    return hashlib.sha512(content).hexdigest()


def test_upload_computes_initial_hashes(client: TestClient, case: Case):
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 201
    body = resp.json()
    assert body["sha256"] == _sha256(FAKE_MP4)
    assert body["sha512"] == _sha512(FAKE_MP4)
    assert body["hash_calculated_at"] is not None


def test_hash_endpoint_returns_both_algorithms(client: TestClient, case: Case):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]

    resp = client.post(f"/api/v1/evidence/{evidence_id}/hash")
    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence_id"] == evidence_id
    assert len(body["calculations"]) == 2
    assert {c["algorithm"] for c in body["calculations"]} == {"SHA-256", "SHA-512"}

    for calc in body["calculations"]:
        assert calc["file_size"] == len(FAKE_MP4)
        assert calc["calculated_at"] is not None

    sha256 = next(c for c in body["calculations"] if c["algorithm"] == "SHA-256")
    assert sha256["hash"] == _sha256(FAKE_MP4)


def test_hash_endpoint_updates_recorded_integrity(
    client: TestClient, case: Case, db_session: Session
):
    evidence_id = uuid.UUID(upload(client, case.id, FAKE_MP4).json()["id"])

    resp = client.post(f"/api/v1/evidence/{evidence_id}/hash")
    assert resp.status_code == 200

    evidence = db_session.get(Evidence, evidence_id)
    assert evidence is not None
    assert evidence.sha256 == _sha256(FAKE_MP4)
    assert evidence.sha512 == _sha512(FAKE_MP4)
    assert evidence.hash_calculated_at is not None


def test_hash_endpoint_writes_audit_log(client: TestClient, case: Case, db_session: Session):
    evidence_id = upload(client, case.id, FAKE_MP4).json()["id"]
    client.post(f"/api/v1/evidence/{evidence_id}/hash")

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "evidence.hash")
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.entity_type == "evidence"
    assert entry.entity_id == uuid.UUID(evidence_id)


def test_hash_endpoint_unknown_evidence_404(client: TestClient):
    resp = client.post(f"/api/v1/evidence/{uuid.uuid4()}/hash")
    assert resp.status_code == 404


def test_hash_endpoint_missing_storage_file_404(
    client: TestClient, case: Case, db_session: Session
):
    evidence_id = uuid.UUID(upload(client, case.id, FAKE_MP4).json()["id"])
    evidence = db_session.get(Evidence, evidence_id)
    assert evidence is not None
    evidence.storage_path = "nonexistent/path/that/does/not/exist.mp4"
    db_session.commit()

    resp = client.post(f"/api/v1/evidence/{evidence_id}/hash")
    assert resp.status_code == 404
