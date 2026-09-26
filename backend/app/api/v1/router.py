from fastapi import APIRouter

from app.api.v1.endpoints import (
    analysis,
    audit,
    auth,
    cases,
    comparison,
    dashboard,
    evidence,
    health,
    reports,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(cases.router)
api_router.include_router(evidence.router)
api_router.include_router(analysis.router)
api_router.include_router(dashboard.router)
api_router.include_router(comparison.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
