import json
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AnalysisError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 600


def resolve_tool(configured: str, default_name: str) -> str:
    """Resolve an FFmpeg tool: absolute configured path, else PATH lookup."""
    if configured and configured != default_name:
        candidate = Path(configured)
        if candidate.is_file():
            return str(candidate)
    resolved = shutil.which(configured or default_name)
    if resolved:
        return resolved
    raise AnalysisError(
        f"Could not locate '{default_name}'. Install FFmpeg or set the path in configuration."
    )


def resolve_ffprobe() -> str:
    return resolve_tool(settings.ffprobe_path, "ffprobe")


def resolve_ffmpeg() -> str:
    return resolve_tool(settings.ffmpeg_path, "ffmpeg")


def probe_video(path: str | Path) -> dict:
    """Return ffprobe JSON for container format and all streams of a media file."""
    binary = resolve_ffprobe()
    file_path = Path(path)
    if not file_path.is_file():
        raise NotFoundError("Video file is missing from storage")
    command = [
        binary,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    return _run_json(command)


def probe_keyframes(path: str | Path) -> dict:
    """Return frame-level ffprobe info for the first video stream.

    Used to derive keyframe/GOP structure. Includes only cheap per-frame fields.
    """
    binary = resolve_ffprobe()
    file_path = Path(path)
    if not file_path.is_file():
        raise NotFoundError("Video file is missing from storage")
    command = [
        binary,
        "-v",
        "error",
        "-print_format",
        "json",
        "-select_streams",
        "v:0",
        "-show_frames",
        "-show_entries",
        "frame=key_frame,pts_time,pict_type",
        str(file_path),
    ]
    return _run_json(command)


def _run_json(command: list[str]) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        raise AnalysisError(f"FFprobe binary could not be executed: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AnalysisError("FFprobe timed out while analyzing the file") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:500]
        raise AnalysisError(f"FFprobe could not analyze the file: {detail}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AnalysisError("FFprobe produced invalid JSON output") from exc
