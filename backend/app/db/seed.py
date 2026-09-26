"""Initial data seeding.

Run via: python -m app.db.seed [--if-absent]

The bootstrap admin is configured through ADMIN_EMAIL / ADMIN_PASSWORD. When no
password is supplied a cryptographically random one is generated, written to
``storage/.admin_credentials`` with mode 0600, and never printed. An existing
admin is never modified, so container restarts cannot reset a password that an
operator has since changed.
"""

import argparse
import os
import secrets
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import CaseStatus, UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Case, User

DEMO_CASE_NUMBER = "CASE-0001"


def generate_admin_password() -> str:
    """Return a random password. 32 url-safe characters."""
    return secrets.token_urlsafe(24)


def write_credentials_file(path: Path, email: str, password: str) -> None:
    """Write the generated credentials to ``path`` with mode 0600.

    The file is created with 0600 from the outset and chmod'ed afterwards so an
    existing, more permissive file cannot survive.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# CCTV Forensic Analyzer - bootstrap admin credentials\n"
        "# Generated on first seed because ADMIN_PASSWORD was not set.\n"
        "# Delete this file once you have changed the password.\n"
        f"email={email}\n"
        f"password={password}\n"
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)


def admin_exists(db: Session, email: str | None = None) -> bool:
    return (
        db.execute(select(User.id).where(User.email == (email or settings.admin_email)))
        .first()
        is not None
    )


def get_or_create_admin(
    db: Session,
    *,
    email: str | None = None,
    password: str | None = None,
    credentials_file: Path | None = None,
) -> User:
    """Return the bootstrap admin, creating it only if it does not exist.

    An existing admin is returned untouched: seeding must never reset a
    password that has been changed after the first boot.
    """
    email = email or settings.admin_email
    admin = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if admin is not None:
        return admin

    configured = password if password is not None else settings.admin_password
    generated = not configured
    if generated:
        configured = generate_admin_password()

    admin = User(
        name="Administrator",
        email=email,
        password_hash=hash_password(configured),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    try:
        db.commit()
    except IntegrityError:
        # Concurrent seed (backend and worker start together). The unique index
        # on users.email kept the database consistent; re-read the winner.
        db.rollback()
        existing = db.execute(select(User).where(User.email == email)).scalar_one()
        print(f"Admin user already present (created concurrently): {email}")
        return existing
    db.refresh(admin)

    if generated:
        target = credentials_file or settings.admin_credentials_file
        try:
            write_credentials_file(target, email, configured)
        except OSError as exc:
            # Failing loudly beats creating an admin nobody can log into.
            raise RuntimeError(
                f"Created admin '{email}' with a generated password but could not "
                f"write it to {target}: {exc}. Set ADMIN_PASSWORD explicitly, or "
                "make the storage directory writable, then re-run the seed."
            ) from exc
        print(f"Admin user created: {email}")
        print(f"Admin credentials written to {target} (mode 0600)")
    else:
        print(f"Admin user created: {email} (password taken from ADMIN_PASSWORD)")

    return admin


def get_or_create_demo_case(db: Session, admin: User) -> Case:
    case = (
        db.execute(select(Case).where(Case.case_number == DEMO_CASE_NUMBER))
        .scalar_one_or_none()
    )
    if case is None:
        case = Case(
            case_number=DEMO_CASE_NUMBER,
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


def seed(*, only_if_absent: bool = False) -> bool:
    """Ensure bootstrap data exists.

    Returns True when an admin was created, False when one already existed.
    With ``only_if_absent`` the run is a no-op if any admin is present.
    """
    settings.ensure_storage_dirs()
    db = SessionLocal()
    try:
        if only_if_absent and admin_exists(db):
            print("Admin user already exists; leaving it untouched.")
            return False
        before = admin_exists(db)
        admin = get_or_create_admin(db)
        get_or_create_demo_case(db, admin)
        return not before
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed bootstrap data.")
    parser.add_argument(
        "--if-absent",
        action="store_true",
        help="Do nothing if an admin user already exists (used by the container "
        "entrypoint so restarts never touch an existing account).",
    )
    args = parser.parse_args(argv)
    seed(only_if_absent=args.if_absent)
    print("Seeding complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
