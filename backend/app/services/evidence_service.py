import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import EvidenceStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Analysis, Case, Evidence
from app.schemas.evidence import EvidenceListItem
from app.utils.file_utils import generate_evidence_number


def to_evidence_list_item(evidence: Evidence) -> EvidenceListItem:
    case = evidence.case
    return EvidenceListItem(
        id=evidence.id,
        evidence_number=evidence.evidence_number,
        case_id=evidence.case_id,
        case_number=case.case_number if case else None,
        case_title=case.title if case else None,
        original_filename=evidence.original_filename,
        file_size=evidence.file_size,
        mime_type=evidence.mime_type,
        sha256=evidence.sha256,
        status=evidence.status,
        uploaded_at=evidence.uploaded_at,
    )


def get_case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise NotFoundError("Case not found")
    return case


def get_evidence_or_404(db: Session, evidence_id: uuid.UUID) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise NotFoundError("Evidence not found")
    return evidence


def create_evidence(
    db: Session,
    *,
    case_id: uuid.UUID,
    original_filename: str,
    stored_filename: str,
    file_size: int,
    mime_type: str,
    storage_path: str,
    uploaded_by: uuid.UUID,
    sha256: str | None = None,
    sha512: str | None = None,
    hash_calculated_at: datetime | None = None,
) -> Evidence:
    evidence_number = _unique_evidence_number(db)
    evidence = Evidence(
        case_id=case_id,
        evidence_number=evidence_number,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size=file_size,
        mime_type=mime_type,
        storage_path=storage_path,
        sha256=sha256,
        sha512=sha512,
        hash_calculated_at=hash_calculated_at,
        status=EvidenceStatus.UPLOADED,
        uploaded_by=uploaded_by,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def _unique_evidence_number(db: Session) -> str:
    for _ in range(5):
        candidate = generate_evidence_number()
        exists = db.execute(
            select(Evidence).where(Evidence.evidence_number == candidate)
        ).scalar_one_or_none()
        if exists is None:
            return candidate
    raise ConflictError("Could not generate a unique evidence number")


def list_evidence(
    db: Session,
    *,
    page: int,
    page_size: int,
    case_id: uuid.UUID | None = None,
    status: EvidenceStatus | None = None,
    search: str | None = None,
) -> tuple[list[Evidence], int]:
    """List evidence with filters and pagination.

    Soft-deleted evidence is hidden unless explicitly requested via `status`.
    """
    filters = []
    if status is not None:
        filters.append(Evidence.status == status)
    else:
        filters.append(Evidence.status != EvidenceStatus.DELETED)
    if case_id is not None:
        filters.append(Evidence.case_id == case_id)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Evidence.evidence_number.ilike(pattern),
                Evidence.original_filename.ilike(pattern),
                Case.case_number.ilike(pattern),
                Case.title.ilike(pattern),
            )
        )

    base = select(Evidence).join(Evidence.case).where(*filters)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

    items = (
        db.execute(
            base.options(joinedload(Evidence.case))
            .order_by(Evidence.uploaded_at.desc(), Evidence.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )
    return list(items), total


def get_evidence_detail(db: Session, evidence_id: uuid.UUID) -> Evidence:
    """Fetch an evidence with its video metadata and analyses preloaded."""
    evidence = db.execute(
        select(Evidence)
        .where(Evidence.id == evidence_id)
        .options(
            joinedload(Evidence.case),
            selectinload(Evidence.video_metadata),
            selectinload(Evidence.analyses),
        )
    ).scalar_one_or_none()
    if evidence is None:
        raise NotFoundError("Evidence not found")
    return evidence


def soft_delete_evidence(db: Session, evidence: Evidence) -> Evidence:
    """Soft-delete evidence, preserving the file and history for chain of custody."""
    evidence.status = EvidenceStatus.DELETED
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def list_analyses(db: Session, evidence_id: uuid.UUID) -> list[Analysis]:
    return list(
        db.execute(
            select(Analysis)
            .where(Analysis.evidence_id == evidence_id)
            .order_by(Analysis.started_at.desc().nulls_last(), Analysis.id)
        )
        .scalars()
        .all()
    )
