import os
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuditLog, Case, Evidence
from tests.helpers import FAKE_MP4, upload


def stored_evidence(db_session: Session, evidence_id: uuid.UUID) -> Evidence:
    evidence = db_session.get(Evidence, evidence_id)
    assert evidence is not None
    return evidence


# --- happy path ---


def test_upload_valid_video(client: TestClient, case: Case, db_session: Session):
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 201
    body = resp.json()
    assert body["evidence_number"].startswith("EVD-")
    assert body["original_filename"] == "clip.mp4"
    assert body["mime_type"] == "video/mp4"
    assert body["file_size"] == len(FAKE_MP4)
    assert body["status"] == "uploaded"
    assert "storage_path" not in body

    evidence = stored_evidence(db_session, uuid.UUID(body["id"]))
    assert evidence.storage_path != ""
    assert evidence.case_id == case.id


def test_upload_stored_file_is_readonly(client: TestClient, case: Case, db_session: Session):
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 201
    evidence = stored_evidence(db_session, uuid.UUID(resp.json()["id"]))
    path = Path(evidence.storage_path)
    assert path.exists()
    assert os.access(path, os.W_OK) is False


def test_upload_writes_audit_log(client: TestClient, case: Case, db_session: Session):
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 201
    evidence_id = uuid.UUID(resp.json()["id"])

    entry = db_session.execute(
        select(AuditLog).where(AuditLog.action == "evidence.upload")
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.entity_type == "evidence"
    assert entry.entity_id == evidence_id
    assert entry.details["original_filename"] == "clip.mp4"


def test_upload_never_overwrites(client: TestClient, case: Case, db_session: Session):
    first = upload(client, case.id, FAKE_MP4)
    second = upload(client, case.id, FAKE_MP4)
    assert first.status_code == 201
    assert second.status_code == 201

    first_evidence = stored_evidence(db_session, uuid.UUID(first.json()["id"]))
    second_evidence = stored_evidence(db_session, uuid.UUID(second.json()["id"]))
    assert first_evidence.storage_path != second_evidence.storage_path
    assert Path(first_evidence.storage_path).exists()
    assert Path(second_evidence.storage_path).exists()


def test_upload_sanitizes_path_traversal(client: TestClient, case: Case, db_session: Session):
    resp = upload(client, case.id, FAKE_MP4, filename="..\\..\\..\\evil.mp4")
    assert resp.status_code == 201
    assert resp.json()["original_filename"] == "evil.mp4"
    evidence = stored_evidence(db_session, uuid.UUID(resp.json()["id"]))
    stored = Path(evidence.storage_path)
    assert ".." not in str(stored.resolve()).split("evil.mp4")[0].replace("\\", "/").split("/")[-2:]


# --- rejection paths ---


def test_upload_rejects_invalid_extension(client: TestClient, case: Case):
    resp = upload(client, case.id, FAKE_MP4, filename="clip.exe")
    assert resp.status_code == 422


def test_upload_rejects_non_video_content(client: TestClient, case: Case):
    resp = upload(client, case.id, b"this is definitely not a video")
    assert resp.status_code == 422


def test_upload_rejects_empty_file(client: TestClient, case: Case):
    resp = upload(client, case.id, b"")
    assert resp.status_code == 422


def test_upload_rejects_oversized_file(client: TestClient, case: Case, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size", 50)
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 413


def test_upload_rejects_unknown_case(client: TestClient):
    resp = upload(client, uuid.uuid4(), FAKE_MP4)
    assert resp.status_code == 404


def test_rejected_file_is_quarantined(client: TestClient, case: Case):
    upload(client, case.id, b"this is definitely not a video")
    quarantine_files = list(settings.storage_quarantine_dir.glob("*.bin"))
    assert len(quarantine_files) == 1


# --- working copy ---


def test_working_copy_created_for_analysis(client: TestClient, case: Case, db_session: Session):
    resp = upload(client, case.id, FAKE_MP4)
    assert resp.status_code == 201
    evidence = stored_evidence(db_session, uuid.UUID(resp.json()["id"]))

    from app.services.storage_service import StorageService

    copy = StorageService().create_working_copy(evidence)
    assert copy.exists()
    assert copy.stat().st_size == evidence.file_size
    original = Path(evidence.storage_path)
    assert original.exists()
    assert copy.resolve() != original.resolve()
