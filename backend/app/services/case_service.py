import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import CaseStatus
from app.core.exceptions import ConflictError
from app.models import Case
from app.schemas.case import CaseCreate


def _generate_case_number() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"CSE-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


def create_case(db: Session, *, body: CaseCreate) -> Case:
    case_number = body.case_number
    if case_number is None:
        case_number = _unique_case_number(db)
    elif (
        db.execute(select(Case).where(Case.case_number == case_number)).scalar_one_or_none()
        is not None
    ):
        raise ConflictError("A case with this number already exists")

    case = Case(
        case_number=case_number,
        title=body.title,
        description=body.description,
        status=CaseStatus.OPEN,
        investigator_id=body.investigator_id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _unique_case_number(db: Session) -> str:
    for _ in range(5):
        candidate = _generate_case_number()
        exists = db.execute(select(Case).where(Case.case_number == candidate)).scalar_one_or_none()
        if exists is None:
            return candidate
    raise ConflictError("Could not generate a unique case number")


def list_cases(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[list[Case], int]:
    stmt = select(Case)
    count_stmt = select(func.count(Case.id))
    if search:
        pattern = f"%{search}%"
        where = or_(
            Case.case_number.ilike(pattern),
            Case.title.ilike(pattern),
            Case.description.ilike(pattern),
        )
        stmt = stmt.where(where)
        count_stmt = count_stmt.where(where)
    total = db.execute(count_stmt).scalar_one()
    cases = (
        db.execute(
            stmt.order_by(Case.created_at.desc(), Case.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(cases), total
