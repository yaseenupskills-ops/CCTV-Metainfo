import sqlalchemy as sa
from sqlalchemy.orm import Session

EXPECTED_TABLES = {
    "users",
    "cases",
    "evidence",
    "video_metadata",
    "analyses",
    "anomalies",
    "comparisons",
    "reports",
    "audit_logs",
}


def test_all_tables_created(db_session: Session):
    inspector = sa.inspect(db_session.bind)
    assert inspector is not None
    tables = set(inspector.get_table_names())
    assert tables >= EXPECTED_TABLES


def test_models_can_be_written_and_read(db_session: Session):
    from app.core.enums import CaseStatus, UserRole
    from app.models import Case, User

    user = User(
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-hash",
        role=UserRole.INVESTIGATOR,
    )
    db_session.add(user)
    db_session.flush()

    case = Case(
        case_number="CASE-9999",
        title="Test Case",
        status=CaseStatus.OPEN,
        investigator_id=user.id,
    )
    db_session.add(case)
    db_session.commit()

    loaded = db_session.get(Case, case.id)
    assert loaded is not None
    assert loaded.title == "Test Case"
    assert loaded.investigator is not None
    assert loaded.investigator.email == "test@example.com"
