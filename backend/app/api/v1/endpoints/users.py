import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import AdminUser, DbSession
from app.schemas.auth import UserCreate, UserRead, UserUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.audit_service import AuditService
from app.services.auth_service import (
    create_user,
    get_user_or_404,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserRead])
def list_users_endpoint(
    db: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[UserRead]:
    """Admin-only: list users."""
    users, total = list_users(db, page=page, page_size=page_size)
    return PaginatedResponse[UserRead](
        items=[UserRead.model_validate(user) for user in users],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=UserRead, status_code=201)
def create_user_endpoint(
    db: DbSession,
    request: Request,
    actor: AdminUser,
    body: UserCreate,
) -> UserRead:
    """Admin-only: create a user account."""
    user = create_user(
        db,
        name=body.name,
        email=body.email,
        password=body.password,
        role=body.role,
    )
    AuditService.record(
        db,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"email": user.email, "role": user.role.value},
    )
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(
    db: DbSession,
    _: AdminUser,
    user_id: uuid.UUID,
) -> UserRead:
    """Admin-only: return a single user."""
    return UserRead.model_validate(get_user_or_404(db, user_id))


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    db: DbSession,
    request: Request,
    actor: AdminUser,
    user_id: uuid.UUID,
    body: UserUpdate,
) -> UserRead:
    """Admin-only: update a user's name, role, or password."""
    user = get_user_or_404(db, user_id)
    updated = update_user(
        db,
        user,
        name=body.name,
        role=body.role,
        password=body.password,
    )
    AuditService.record(
        db,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        user_id=actor.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"role": updated.role.value},
    )
    return UserRead.model_validate(updated)
