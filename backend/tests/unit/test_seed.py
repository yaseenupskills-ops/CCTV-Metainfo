from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core.enums import CaseStatus, UserRole
from app.core.security import verify_password


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


# --- ADMIN_EMAIL / ADMIN_PASSWORD ---------------------------------------


def test_generates_random_password_when_none_configured(
    db_session: Session, tmp_path: Path
):
    """No ADMIN_PASSWORD: generate one and persist it to the credentials file."""
    from app.db.seed import get_or_create_admin

    creds = tmp_path / ".admin_credentials"
    admin = get_or_create_admin(db_session, email="ops@example.com", password="",
                                credentials_file=creds)

    assert creds.is_file()
    body = creds.read_text()
    assert "email=ops@example.com" in body
    generated = body.split("password=", 1)[1].strip()
    assert len(generated) >= 16
    # The stored hash must actually accept the generated password.
    assert verify_password(generated, admin.password_hash)


def test_generated_credentials_file_is_owner_only(db_session: Session, tmp_path: Path):
    import stat

    from app.db.seed import get_or_create_admin

    creds = tmp_path / ".admin_credentials"
    get_or_create_admin(db_session, password="", credentials_file=creds)

    assert stat.S_IMODE(creds.stat().st_mode) == 0o600


def test_generated_password_is_never_printed(
    db_session: Session, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """The password must not reach stdout/stderr (it lands in docker logs)."""
    from app.db.seed import get_or_create_admin

    creds = tmp_path / ".admin_credentials"
    get_or_create_admin(db_session, password="", credentials_file=creds)
    generated = creds.read_text().split("password=", 1)[1].strip()

    captured = capsys.readouterr()
    assert generated not in captured.out
    assert generated not in captured.err


def test_configured_password_is_used_and_not_written_to_disk(
    db_session: Session, tmp_path: Path
):
    from app.db.seed import get_or_create_admin

    creds = tmp_path / ".admin_credentials"
    admin = get_or_create_admin(
        db_session, email="ops@example.com", password="Supplied-Correct-Horse",
        credentials_file=creds,
    )

    assert verify_password("Supplied-Correct-Horse", admin.password_hash)
    # Operator already has the password; no file should be created.
    assert not creds.exists()


def test_rerun_does_not_reset_an_existing_admin_password(db_session: Session):
    """A container restart must never clobber a changed password."""
    from app.db.seed import get_or_create_admin

    first = get_or_create_admin(db_session, email="ops@example.com", password="First-Pass-1")
    original_hash = first.password_hash

    # Operator changes it, then the container restarts with a new configured value.
    second = get_or_create_admin(
        db_session, email="ops@example.com", password="Rotated-Second-2"
    )

    assert second.id == first.id
    assert second.password_hash == original_hash
    assert not verify_password("Rotated-Second-2", second.password_hash)
    assert verify_password("First-Pass-1", second.password_hash)


def test_admin_exists(db_session: Session):
    from app.db.seed import admin_exists, get_or_create_admin

    assert admin_exists(db_session, email="ops@example.com") is False
    get_or_create_admin(db_session, email="ops@example.com", password="Whatever-1234")
    assert admin_exists(db_session, email="ops@example.com") is True


def test_seed_only_if_absent_skips_existing_admin(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
):
    from app.db import seed as seed_module

    monkeypatch.setattr(seed_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(seed_module.settings, "admin_email", "ops@example.com")
    monkeypatch.setattr(seed_module.settings, "admin_password", "Original-Pass-9")

    created_first = seed_module.seed(only_if_absent=True)
    created_second = seed_module.seed(only_if_absent=True)

    assert created_first is True
    assert created_second is False


def test_unwritable_credentials_path_raises(db_session: Session, tmp_path: Path):
    """Better to fail the boot than silently create an unreachable admin."""
    from app.db.seed import get_or_create_admin

    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)  # read + execute only: cannot create a file inside
    try:
        with pytest.raises(RuntimeError, match="could not write it to"):
            get_or_create_admin(
                db_session, password="", credentials_file=blocked / ".admin_credentials"
            )
    finally:
        blocked.chmod(0o700)


def test_two_generated_passwords_differ(db_session: Session, tmp_path: Path):
    from app.db.seed import generate_admin_password

    assert generate_admin_password() != generate_admin_password()


def test_generated_password_satisfies_schema_min_length():
    """Generated passwords must be usable by the login schema."""
    from app.db.seed import generate_admin_password

    assert len(generate_admin_password()) >= 8
