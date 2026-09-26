"""Shared API dependencies: database sessions and authentication/RBAC."""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resolve the authenticated user from a Bearer token."""
    if credentials is None:
        raise UnauthorizedError("Authentication required")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid authentication token") from exc
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Invalid authentication token")
    return user


def require_roles(*roles: UserRole):
    """Return a dependency that only allows users with one of the given roles."""

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise ForbiddenError("Insufficient permissions")
        return current_user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
StaffUser = Annotated[User, Depends(require_roles(UserRole.INVESTIGATOR, UserRole.ADMIN))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]

__all__ = [
    "DbSession",
    "get_db",
    "get_current_user",
    "require_roles",
    "CurrentUser",
    "StaffUser",
    "AdminUser",
]
