import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.core.exceptions import NotFoundError

_CHUNK_SIZE = 1024 * 1024  # 1 MB


def _hash_file(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as source:
        while True:
            chunk = source.read(_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_hashes(path: str | Path) -> dict:
    """Compute SHA-256 and SHA-512 hashes of a file, streaming in chunks.

    Hashes are always computed from the actual stored bytes of the original
    evidence file — never from a cache.
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise NotFoundError("Evidence file is missing from storage")

    return {
        "sha256": _hash_file(file_path, "sha256"),
        "sha512": _hash_file(file_path, "sha512"),
        "file_size": file_path.stat().st_size,
        "calculated_at": datetime.now(UTC),
    }
