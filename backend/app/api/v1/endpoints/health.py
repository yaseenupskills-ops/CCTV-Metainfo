from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: DbSession) -> dict[str, str]:
    """Return service and database health status."""
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    return {"status": "ok", "database": database}
