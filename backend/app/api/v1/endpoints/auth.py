from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.exceptions import RateLimitError, UnauthorizedError
from app.core.rate_limit import check_rate_limit, parse_rate_limit
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.audit_service import AuditService
from app.services.auth_service import authenticate_user, issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    db: DbSession,
    request: Request,
    body: LoginRequest,
) -> TokenResponse:
    ip_address = request.client.host if request.client else "unknown"
    max_hits, window_seconds = parse_rate_limit(settings.login_rate_limit)
    if not check_rate_limit(
        key=ip_address,
        action="login",
        max_hits=max_hits,
        window_seconds=window_seconds,
    ):
        raise RateLimitError("Too many login attempts. Try again later.")

    email = body.email.strip().lower()
    user_agent = request.headers.get("user-agent")

    user = authenticate_user(db, email=email, password=body.password)
    if user is None:
        AuditService.record(
            db,
            action="auth.login_failed",
            entity_type="user",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email},
        )
        raise UnauthorizedError("Invalid email or password")

    token = issue_token(user)
    AuditService.record(
        db,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return TokenResponse(access_token=token["access_token"], user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
