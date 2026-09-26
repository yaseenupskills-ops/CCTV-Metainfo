"""Startup guards for secret configuration.

The application must refuse to start when JWT_SECRET is missing or is still one
of the placeholders shipped in .env.example. Without this, every token would be
signed with a publicly known key.
"""

import pytest

from app.core.config import settings
from app.main import _FORBIDDEN_SECRETS, _reject_placeholder_secrets

pytestmark = pytest.mark.security


def test_rejects_empty_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "")

    with pytest.raises(RuntimeError, match="JWT_SECRET is not set"):
        _reject_placeholder_secrets()


def test_rejects_whitespace_only_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "   ")

    with pytest.raises(RuntimeError, match="JWT_SECRET is not set"):
        _reject_placeholder_secrets()


@pytest.mark.parametrize("placeholder", sorted(_FORBIDDEN_SECRETS))
def test_rejects_shipped_placeholders(
    placeholder: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The historical config.py default and the .env.example placeholders."""
    monkeypatch.setattr(settings, "jwt_secret", placeholder)

    with pytest.raises(RuntimeError, match="placeholder"):
        _reject_placeholder_secrets()


def test_placeholder_check_is_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "CHANGE_ME_GENERATE_A_LONG_RANDOM_STRING")

    with pytest.raises(RuntimeError, match="placeholder"):
        _reject_placeholder_secrets()


def test_accepts_a_real_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "a" * 64)

    _reject_placeholder_secrets()  # must not raise


def test_config_default_is_empty_not_the_old_hardcoded_value() -> None:
    """config.py must not reintroduce a usable default for jwt_secret."""
    from app.core.config import Settings

    assert Settings.model_fields["jwt_secret"].default == ""


def test_no_forbidden_entry_is_a_plausible_secret() -> None:
    """Guard against someone adding a real-looking secret to the deny list."""
    for entry in _FORBIDDEN_SECRETS:
        assert len(entry) < 64, f"deny-list entry looks like a real secret: {entry!r}"
