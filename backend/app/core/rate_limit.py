"""Lightweight in-memory sliding-window rate limiter.

This is sufficient for single-process deployments and the test suite. A
production deployment behind multiple workers/processes should replace this
with a distributed limiter backed by Redis (see ``app/workers``).

Usage::

    if not check_rate_limit(key=client_ip, action="login"):
        raise RateLimitError("Too many login attempts")
"""

import threading
import time
from collections import deque

_hits: dict[tuple[str, str], deque[float]] = {}
_lock = threading.Lock()


def parse_rate_limit(value: str) -> tuple[int, float]:
    """Parse a ``"N/unit"`` spec into ``(max_hits, window_seconds)``.

    Supported units: second, minute, hour, day (singular or plural).
    """
    count_text, _, unit = value.strip().lower().partition("/")
    if not count_text.isdigit() or not unit:
        raise ValueError(f"Invalid rate limit spec: {value!r}")
    max_hits = int(count_text)
    unit_seconds = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
        "day": 86400,
        "days": 86400,
    }
    if unit not in unit_seconds:
        raise ValueError(f"Invalid rate limit unit: {unit!r}")
    return max_hits, unit_seconds[unit]


def check_rate_limit(*, key: str, action: str, max_hits: int, window_seconds: float) -> bool:
    """Record a hit and return True when the caller is allowed to proceed."""
    now = time.monotonic()
    cache_key = (key, action)
    with _lock:
        timestamps = _hits.setdefault(cache_key, deque())
        while timestamps and now - timestamps[0] > window_seconds:
            timestamps.popleft()
        if len(timestamps) >= max_hits:
            return False
        timestamps.append(now)
        return True


def reset_rate_limits() -> None:
    """Clear all recorded hits (used by tests and the auth reset endpoint)."""
    with _lock:
        _hits.clear()
