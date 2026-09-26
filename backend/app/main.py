from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.middleware import RequestSizeLimitMiddleware

configure_logging()

# Values that must never be used to sign JWTs. The first is the historical
# default from config.py; the rest are the placeholders shipped in .env.example.
_FORBIDDEN_SECRETS = frozenset(
    {
        "change_me_generate_a_long_random_string",
        "change_me",
        "replace_with_openssl_rand_hex_32",
        "changeme",
        "secret",
    }
)


def _reject_placeholder_secrets() -> None:
    """Refuse to start if JWT_SECRET is unset or still a shipped placeholder.

    Raises RuntimeError on misconfiguration so the app fails fast and loudly
    instead of silently signing tokens with a publicly known key.
    """
    secret = settings.jwt_secret
    if not secret or not secret.strip():
        raise RuntimeError(
            "JWT_SECRET is not set. The application refuses to start without it, "
            "because every token would be signed with a publicly known key.\n"
            "Generate one with:\n"
            '    python -c "import secrets; print(secrets.token_hex(32))"\n'
            "then set JWT_SECRET in your .env file (see .env.example)."
        )
    if secret.strip().lower() in _FORBIDDEN_SECRETS:
        raise RuntimeError(
            "JWT_SECRET is still set to a placeholder value. Generate a real one "
            'with: python -c "import secrets; print(secrets.token_hex(32))"'
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    _reject_placeholder_secrets()
    settings.ensure_storage_dirs()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.app_debug,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestSizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "User-Agent", "Accept", "Origin"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
