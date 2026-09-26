from sqlalchemy.orm import Session

from app.core.enums import CaseStatus, UserRole


def test_seed_creates_admin(db_session: Session):
    from app.db.seed import get_or_create_admin

    admin = get_or_create_admin(db_session)
    assert admin.role == UserRole.ADMIN
    assert admin.email == "admin@cctv.local"


def test_seed_is_idempotent(db_session: Session):
    from app.db.seed import get_or_create_admin

    first = get_or_create_admin(db_session)
    second = get_or_create_admin(db_session)
    assert first.id == second.id


def test_seed_creates_demo_case(db_session: Session):
    from app.db.seed import get_or_create_admin, get_or_create_demo_case

    admin = get_or_create_admin(db_session)
    case = get_or_create_demo_case(db_session, admin)
    assert case.case_number == "CASE-0001"
    assert case.status == CaseStatus.OPEN
    assert case.investigator_id == admin.id
