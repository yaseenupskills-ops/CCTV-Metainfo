from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_secret,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("SuperSecret123!")
    assert hashed != "SuperSecret123!"
    assert verify_password("SuperSecret123!", hashed)


def test_password_hash_rejects_wrong_password():
    hashed = hash_password("SuperSecret123!")
    assert not verify_password("WrongPassword", hashed)


def test_generate_secret_is_unique_and_sufficient_length():
    first = generate_secret()
    second = generate_secret()
    assert first != second
    assert len(first) >= 32


def test_access_token_roundtrip():
    token = create_access_token("user-123", "admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_token_is_rejected():
    token = create_access_token("user-123", "admin", expires_delta=timedelta(minutes=-5))
    try:
        decode_access_token(token)
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("expected UnauthorizedError for expired token")


def test_token_with_wrong_secret_is_rejected():
    token = jwt.encode(
        {"sub": "user-123", "role": "admin", "type": "access"},
        "a-totally-different-secret-that-is-long-enough-123",
        algorithm=settings.jwt_algorithm,
    )
    try:
        decode_access_token(token)
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("expected UnauthorizedError for bad signature")


def test_non_access_token_is_rejected():
    token = jwt.encode(
        {"sub": "user-123", "role": "admin", "type": "refresh"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    try:
        decode_access_token(token)
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("expected UnauthorizedError for non-access token")
