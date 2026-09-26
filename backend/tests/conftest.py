import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models as app_models  # noqa: F401  (register models on Base.metadata)
from app.core.enums import CaseStatus, UserRole
from app.core.exceptions import AnalysisError
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Case, User

# StaticPool keeps a single in-memory SQLite connection shared across threads,
# which is required because FastAPI runs sync endpoints in a threadpool.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


@pytest.fixture(autouse=True)
def _test_storage(tmp_path, monkeypatch):
    """Redirect evidence storage to a temp directory so tests never touch real files."""
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "storage_path", tmp_path / "storage")


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear rate-limit counters so tests never interfere with each other."""
    from app.core.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(autouse=True)
def _eager_worker(monkeypatch):
    """Run Celery tasks synchronously and point them at the test database.

    The task opens its own session via ``_session_factory`` so tests redirect
    that factory to the in-memory engine; eager mode keeps execution in-process.
    """
    from app.core.config import settings as app_settings
    from app.workers import tasks as worker_tasks
    from app.workers.celery_app import celery_app

    monkeypatch.setattr(app_settings, "celery_task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(worker_tasks, "_session_factory", TestingSessionLocal)


@pytest.fixture()
def db_session():
    """Yield an isolated database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    """An admin user for authenticating the test client."""
    user = User(
        name="Admin",
        email="admin@test.local",
        password_hash="not-a-real-hash",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def auth_headers(admin_user: User) -> dict[str, str]:
    """Bearer auth headers for the admin test user."""
    from app.core.security import create_access_token

    token = create_access_token(admin_user.id, admin_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def raw_client(db_session):
    """Yield a TestClient without auth headers (login and 401 tests)."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session, raw_client, auth_headers):
    """Yield a TestClient pre-authenticated as an admin user."""
    raw_client.headers.update(auth_headers)
    return raw_client


@pytest.fixture()
def case(db_session: Session) -> Case:
    """A case owned by a non-admin investigator."""
    user = User(
        name="Investigator",
        email="inv@test.local",
        password_hash="not-a-real-hash",
        role=UserRole.INVESTIGATOR,
    )
    db_session.add(user)
    db_session.flush()
    case = Case(
        case_number="CASE-T1",
        title="Test Case",
        status=CaseStatus.OPEN,
        investigator_id=user.id,
    )
    db_session.add(case)
    db_session.commit()
    return case


@pytest.fixture()
def sample_video(tmp_path_factory):
    """Generate a tiny real MP4 (H.264, 1s, 320x240, 10 fps) with FFmpeg.

    Skipped when FFmpeg is unavailable so the suite still runs elsewhere.
    """
    from app.forensic.media import resolve_ffmpeg

    try:
        ffmpeg = resolve_ffmpeg()
    except AnalysisError:
        pytest.skip("FFmpeg not available")
    path = tmp_path_factory.mktemp("samples") / "sample.mp4"
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not path.exists():
        pytest.skip("Could not generate sample video")
    return path


@pytest.fixture()
def video_factory(tmp_path_factory):
    """Generate configurable test videos (duration/fps/size)."""
    from app.forensic.media import resolve_ffmpeg

    try:
        resolve_ffmpeg()
    except AnalysisError:
        pytest.skip("FFmpeg not available")

    from tests.fixtures.generate_samples import video_factory as _factory

    return _factory(tmp_path_factory)


@pytest.fixture()
def scene_change_video_factory(tmp_path_factory):
    """Generate videos with an abrupt black→white scene cut."""
    from app.forensic.media import resolve_ffmpeg

    try:
        resolve_ffmpeg()
    except AnalysisError:
        pytest.skip("FFmpeg not available")

    from tests.fixtures.generate_samples import scene_change_video_factory as _factory

    return _factory(tmp_path_factory)


@pytest.fixture()
def sample_video_family(tmp_path_factory):
    """Generate a related family of sample videos from one base clip."""
    from app.forensic.media import resolve_ffmpeg

    try:
        resolve_ffmpeg()
    except AnalysisError:
        pytest.skip("FFmpeg not available")

    from tests.fixtures.generate_samples import sample_video_family as _factory

    return _factory(tmp_path_factory)


@pytest.fixture()
def seeded_db_session(db_session: Session):
    """Database session pre-populated with the seed data."""
    from app.db.seed import get_or_create_admin, get_or_create_demo_case

    admin = get_or_create_admin(db_session)
    get_or_create_demo_case(db_session, admin)
    return db_session
