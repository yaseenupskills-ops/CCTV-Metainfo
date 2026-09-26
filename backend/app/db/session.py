from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _connect_args() -> dict:
    # connect_timeout is a libpq option; SQLite does not accept it.
    if settings.database_url.startswith("sqlite"):
        return {}
    return {"connect_timeout": 3}


engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args())

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
