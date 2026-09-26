"""Initial data seeding.

Run via: python -m app.db.seed
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import CaseStatus, UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Case, User

ADMIN_EMAIL = "admin@cctv.local"
ADMIN_PASSWORD = "ChangeMe123!"


def get_or_create_admin(db: Session) -> User:
    admin = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one_or_none()
    if admin is None:
        admin = User(
            name="Administrator",
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Created admin user: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    return admin


def get_or_create_demo_case(db: Session, admin: User) -> Case:
    case = db.execute(select(Case).where(Case.case_number == "CASE-0001")).scalar_one_or_none()
    if case is None:
        case = Case(
            case_number="CASE-0001",
            title="Demo Case",
            description="Seed data created for development.",
            status=CaseStatus.OPEN,
            investigator_id=admin.id,
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        print(f"Created demo case: {case.case_number}")
    return case


def seed() -> None:
    settings.ensure_storage_dirs()
    db = SessionLocal()
    try:
        admin = get_or_create_admin(db)
        get_or_create_demo_case(db, admin)
        print("Seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
