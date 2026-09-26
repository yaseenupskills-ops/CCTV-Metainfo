import hashlib
from pathlib import Path

import pytest

from app.core.exceptions import NotFoundError
from app.services.hashing_service import compute_hashes

SHA256_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
SHA512_EMPTY = (
    "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d"
    "0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
)
SHA256_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
SHA512_ABC = (
    "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a219"
    "2992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"
)


def test_hash_known_vector_empty(tmp_path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    result = compute_hashes(path)
    assert result["sha256"] == SHA256_EMPTY
    assert result["sha512"] == SHA512_EMPTY
    assert result["file_size"] == 0


def test_hash_known_vector_abc(tmp_path):
    path = tmp_path / "abc.bin"
    path.write_bytes(b"abc")
    result = compute_hashes(path)
    assert result["sha256"] == SHA256_ABC
    assert result["sha512"] == SHA512_ABC
    assert result["file_size"] == 3


def test_hash_large_file_streaming(tmp_path):
    content = b"\x5a" * (3 * 1024 * 1024)  # 3 MB, spans multiple read chunks
    path = tmp_path / "large.bin"
    path.write_bytes(content)
    result = compute_hashes(path)
    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert result["sha512"] == hashlib.sha512(content).hexdigest()
    assert result["file_size"] == len(content)


def test_hash_missing_file_raises_not_found():
    with pytest.raises(NotFoundError):
        compute_hashes(Path("does/not/exist.bin"))


def test_hash_accepts_string_path(tmp_path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"data")
    result = compute_hashes(str(path))
    assert result["file_size"] == 4
