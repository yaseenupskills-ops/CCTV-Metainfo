from app.forensic.media import probe_keyframes
from app.models import Evidence


def _is_keyframe(frame: dict) -> bool:
    value = frame.get("key_frame")
    return value in (1, "1", True)


def _frame_time(frame: dict) -> float | None:
    """Frame timestamp in seconds from an ffprobe frame entry."""
    value = frame.get("pts_time")
    if value is None or value == "N/A":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_structure(probe_data: dict) -> dict:
    """Derive stream structure statistics from raw ffprobe frame output."""
    frames = probe_data.get("frames", [])

    keyframes = []
    for frame in frames:
        if not _is_keyframe(frame):
            continue
        time = _frame_time(frame)
        if time is not None:
            keyframes.append({"time": round(time, 6), "pict_type": frame.get("pict_type")})

    keyframe_times = [k["time"] for k in keyframes]

    return {
        "keyframe_count": len(keyframes),
        "keyframes": keyframes,
        "frame_count_probed": len(frames),
        "avg_keyframe_interval": (
            round((keyframe_times[-1] - keyframe_times[0]) / max(len(keyframe_times) - 1, 1), 6)
            if len(keyframe_times) > 1
            else None
        ),
        "first_keyframe_time": keyframe_times[0] if keyframe_times else None,
    }


def extract_structure(evidence: Evidence) -> dict:
    """Probe frame-level structure and return parsed statistics."""
    return parse_structure(probe_keyframes(evidence.storage_path))
