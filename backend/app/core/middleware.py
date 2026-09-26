"""HTTP middleware for request hardening."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than a configured limit.

    Multipart uploads are exempt because the evidence upload endpoint enforces
    its own (much larger) ``max_upload_size`` limit and streams the file to
    disk rather than buffering it in memory.
    """

    async def dispatch(self, request: Request, call_next):
        content_type = request.headers.get("content-type", "")
        if request.method in {"POST", "PUT", "PATCH"} and not content_type.startswith(
            "multipart/form-data"
        ):
            content_length = request.headers.get("content-length")
            if (
                content_length
                and content_length.isdigit()
                and int(content_length) > settings.max_request_body_size
            ):
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            f"Request body exceeds the maximum size of "
                            f"{settings.max_request_body_size} bytes"
                        )
                    },
                )
        return await call_next(request)
