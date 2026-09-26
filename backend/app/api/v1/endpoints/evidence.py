import uuid
from math import ceil
from pathlib import Path
from typing import Annotated

import filetype
from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from app.api.deps import AdminUser, CurrentUser, DbSession, StaffUser
from app.core.config import settings
from app.core.enums import EvidenceStatus
from app.core.exceptions import ValidationError
from app.schemas.analysis import AnalysisRead
from app.schemas.anomaly import AnomalyScoreRead
from app.schemas.evidence import (
    EvidenceDetail,
    EvidenceListItem,
    EvidenceRead,
    HashCalculation,
    HashResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.schemas.timeline import TimelineResponse
from app.schemas.video_metadata import MetadataTaskAccepted
from app.services.anomaly_service import get_anomaly_score
from app.services.audit_service import AuditService
from app.services.evidence_service import (
    create_evidence,
    get_case_or_404,
    get_evidence_detail,
    get_evidence_or_404,
    list_analyses,
    list_evidence,
    soft_delete_evidence,
    to_evidence_list_item,
)
from app.services.hashing_service import compute_hashes
from app.services.storage_service import StorageService
from app.services.timeline_service import build_timeline
from app.utils.file_utils import (
    generate_stored_filename,
    sanitize_original_filename,
    validate_extension,
    validate_mime_type,
)
from app.workers.tasks import run_metadata_task

router = APIRouter(prefix="/evidence", tags=["evidence"])
storage_service = StorageService()


@router.get("", response_model=PaginatedResponse[EvidenceListItem])
def list_evidence_endpoint(
    db: DbSession,
    _: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    case_id: uuid.UUID | None = None,
    status: EvidenceStatus | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> PaginatedResponse[EvidenceListItem]:
    """List evidence with optional filters (case, status, free-text search)."""
    items, total = list_evidence(
        db,
        page=page,
        page_size=page_size,
        case_id=case_id,
        status=status,
        search=search,
    )
    return PaginatedResponse[EvidenceListItem](
        items=[to_evidence_list_item(evidence) for evidence in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.get("/{evidence_id}/analysis", response_model=list[AnalysisRead])
def get_evidence_analyses(
    db: DbSession,
    _: CurrentUser,
    evidence_id: uuid.UUID,
) -> list[AnalysisRead]:
    """List the analysis history for an evidence."""
    get_evidence_or_404(db, evidence_id)
    return [AnalysisRead.model_validate(a) for a in list_analyses(db, evidence_id)]


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(
    db: DbSession,
    request: Request,
    actor: AdminUser,
    evidence_id: uuid.UUID,
) -> None:
    """Soft-delete an evidence. The file and history are preserved for chain of custody."""
    evidence = get_evidence_or_404(db, evidence_id)
    soft_delete_evidence(db, evidence)

    AuditService.record(
        db,
        action="evidence.delete",
        entity_type="evidence",
        entity_id=evidence.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"original_filename": evidence.original_filename},
    )


@router.get("/{evidence_id}", response_model=EvidenceDetail)
def get_evidence_detail_endpoint(
    db: DbSession,
    _: CurrentUser,
    evidence_id: uuid.UUID,
) -> EvidenceDetail:
    """Return full evidence details including video metadata and analysis history."""
    evidence = get_evidence_detail(db, evidence_id)
    return EvidenceDetail.model_validate(evidence)


@router.post("/upload", response_model=EvidenceRead, status_code=201)
def upload_evidence(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    file: Annotated[UploadFile, File()],
    case_id: Annotated[uuid.UUID, Form()],
) -> EvidenceRead:
    """Upload an evidence file.

    The original file is stored read-only and never modified. All analysis
    operates on working copies.
    """
    get_case_or_404(db, case_id)

    original_filename = sanitize_original_filename(file.filename or "")
    validate_extension(original_filename)

    header = file.file.read(4096)
    file.file.seek(0)
    guess = filetype.guess(header)
    detected_mime = guess.mime if guess else None
    try:
        validate_mime_type(detected_mime)
    except ValidationError:
        storage_service.quarantine(file.file, reason=f"invalid content mime: {detected_mime}")
        raise

    stored_filename = generate_stored_filename(Path(original_filename).suffix.lower())
    stored = storage_service.store_original(
        file.file,
        str(case_id),
        stored_filename,
        max_size=settings.max_upload_size,
    )

    hashes = compute_hashes(stored["storage_path"])

    evidence = create_evidence(
        db,
        case_id=case_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size=stored["file_size"],
        mime_type=detected_mime or "application/octet-stream",
        storage_path=stored["storage_path"],
        uploaded_by=actor.id,
        sha256=hashes["sha256"],
        sha512=hashes["sha512"],
        hash_calculated_at=hashes["calculated_at"],
    )

    AuditService.record(
        db,
        action="evidence.upload",
        entity_type="evidence",
        entity_id=evidence.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={
            "case_id": str(case_id),
            "original_filename": original_filename,
            "file_size": stored["file_size"],
            "sha256": hashes["sha256"],
        },
    )

    return EvidenceRead.model_validate(evidence)


@router.post("/{evidence_id}/hash", response_model=HashResponse)
def calculate_evidence_hash(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    evidence_id: uuid.UUID,
) -> HashResponse:
    """Recompute SHA-256 and SHA-512 hashes from the actual stored evidence file.

    Results update the recorded integrity values and are audited.
    """
    evidence = get_evidence_or_404(db, evidence_id)
    result = compute_hashes(evidence.storage_path)

    evidence.sha256 = result["sha256"]
    evidence.sha512 = result["sha512"]
    evidence.hash_calculated_at = result["calculated_at"]
    db.commit()
    db.refresh(evidence)

    AuditService.record(
        db,
        action="evidence.hash",
        entity_type="evidence",
        entity_id=evidence.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"sha256": result["sha256"]},
    )

    calculations = [
        HashCalculation(
            algorithm="SHA-256",
            hash=result["sha256"],
            file_size=result["file_size"],
            calculated_at=result["calculated_at"],
        ),
        HashCalculation(
            algorithm="SHA-512",
            hash=result["sha512"],
            file_size=result["file_size"],
            calculated_at=result["calculated_at"],
        ),
    ]
    return HashResponse(evidence_id=evidence.id, calculations=calculations)


@router.post("/{evidence_id}/metadata", response_model=MetadataTaskAccepted)
def extract_evidence_metadata(
    db: DbSession,
    request: Request,
    actor: StaffUser,
    evidence_id: uuid.UUID,
) -> MetadataTaskAccepted:
    """Queue metadata extraction for the background worker.

    FFprobe normalization and stream-structure probing run as a Celery task;
    the response acknowledges the queue. Poll the evidence detail endpoint to
    observe the extracted metadata once the task completes.
    """
    evidence = get_evidence_or_404(db, evidence_id)
    run_metadata_task.delay(evidence_id)

    AuditService.record(
        db,
        action="evidence.metadata_extract",
        entity_type="evidence",
        entity_id=evidence.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"status": "queued"},
    )

    return MetadataTaskAccepted(evidence_id=evidence_id, status="queued")


@router.get("/{evidence_id}/timeline", response_model=TimelineResponse)
def get_evidence_timeline(
    db: DbSession,
    _: CurrentUser,
    evidence_id: uuid.UUID,
) -> TimelineResponse:
    """Return the reconstruction timeline for an evidence.

    Normal segments tile the video duration; anomaly markers are placed at
    frame-difference events from the most recent scene-change analysis. Markers
    are "Potential anomaly" events for expert interpretation, never a verdict.
    """
    evidence = get_evidence_or_404(db, evidence_id)
    return build_timeline(db, evidence)


@router.get("/{evidence_id}/anomaly-score", response_model=AnomalyScoreRead)
def get_evidence_anomaly_score(
    db: DbSession,
    _: CurrentUser,
    evidence_id: uuid.UUID,
) -> AnomalyScoreRead:
    """Return the explainable anomaly indicator score for an evidence.

    The score (0-100) reflects independent technical indicators with their
    weights and reasons. It is labeled an "Anomaly Indicator Score" — never a
    probability of tampering. Null when no scene-change analysis has run.
    """
    evidence = get_evidence_or_404(db, evidence_id)
    return AnomalyScoreRead(
        evidence_id=evidence.id,
        **get_anomaly_score(db, evidence.id),
    )
