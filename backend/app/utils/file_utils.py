import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import ValidationError

ALLOWED_VIDEO_MIMES: set[str] = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/avi",
    "video/x-matroska",
    "video/webm",
}


def sanitize_original_filename(filename: str) -> str:
    """Return only the basename of a user-supplied filename.

    Defeats path-traversal attempts such as `../../evil.mp4` or `C:\\Windows\\evil.mp4`.
    """
    normalized = filename.replace("\\", "/")
    name = Path(normalized).name
    if not name or name in {".", ".."}:
        raise ValidationError("Invalid filename")
    return name


def validate_extension(filename: str) -> str:
    """Validate the file extension against the configured allowlist."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise ValidationError(f"File extension '{ext}' is not allowed")
    return ext


def validate_mime_type(mime: str | None) -> None:
    """Validate the magic-byte-detected MIME type is a supported video format."""
    if mime is None:
        raise ValidationError("File content is not a recognized video format")
    if mime not in ALLOWED_VIDEO_MIMES:
        raise ValidationError(f"File content type '{mime}' is not a supported video format")


def generate_stored_filename(ext: str) -> str:
    """Generate a server-side filename that cannot collide or traverse paths."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{uuid.uuid4().hex}_{timestamp}{ext}"


def generate_evidence_number() -> str:
    """Generate a human-readable unique evidence number."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"EVD-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


def human_size(num: int) -> str:
    """Format a byte count as a human-readable string."""
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.0f} TB"
