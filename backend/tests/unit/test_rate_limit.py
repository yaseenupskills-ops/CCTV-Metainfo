import pytest

from app.core.rate_limit import (
    check_rate_limit,
    parse_rate_limit,
    reset_rate_limits,
)


@pytest.fixture(autouse=True)
def _clean_state():
    reset_rate_limits()
    yield
    reset_rate_limits()


def test_parse_rate_limit_minute():
    assert parse_rate_limit("5/minute") == (5, 60)


def test_parse_rate_limit_hour():
    assert parse_rate_limit("100/hour") == (100, 3600)


def test_parse_rate_limit_seconds_plural():
    assert parse_rate_limit("3/seconds") == (3, 1)


def test_parse_rate_limit_rejects_bad_count():
    with pytest.raises(ValueError):
        parse_rate_limit("abc/minute")


def test_parse_rate_limit_rejects_bad_unit():
    with pytest.raises(ValueError):
        parse_rate_limit("5/fortnight")


def test_allows_requests_under_limit():
    for _ in range(5):
        assert check_rate_limit(key="ip-1", action="login", max_hits=5, window_seconds=60) is True


def test_blocks_requests_over_limit():
    for _ in range(5):
        check_rate_limit(key="ip-2", action="login", max_hits=5, window_seconds=60)
    assert check_rate_limit(key="ip-2", action="login", max_hits=5, window_seconds=60) is False


def test_keys_are_isolated():
    for _ in range(5):
        check_rate_limit(key="ip-3", action="login", max_hits=5, window_seconds=60)
    assert check_rate_limit(key="ip-other", action="login", max_hits=5, window_seconds=60) is True


def test_actions_are_isolated():
    for _ in range(5):
        check_rate_limit(key="ip-4", action="login", max_hits=5, window_seconds=60)
    assert check_rate_limit(key="ip-4", action="other", max_hits=5, window_seconds=60) is True


def test_reset_clears_hits():
    for _ in range(5):
        check_rate_limit(key="ip-5", action="login", max_hits=5, window_seconds=60)
    reset_rate_limits()
    assert check_rate_limit(key="ip-5", action="login", max_hits=5, window_seconds=60) is True


def test_window_expires_hits(monkeypatch):
    now = [1000.0]

    class _Clock:
        @staticmethod
        def monotonic() -> float:
            return now[0]

    monkeypatch.setattr("app.core.rate_limit.time.monotonic", _Clock.monotonic)
    for _ in range(5):
        check_rate_limit(key="ip-6", action="login", max_hits=5, window_seconds=60)
    assert check_rate_limit(key="ip-6", action="login", max_hits=5, window_seconds=60) is False
    now[0] += 61
    assert check_rate_limit(key="ip-6", action="login", max_hits=5, window_seconds=60) is True
