import shutil
import stat
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppError, StorageError
from app.models import Evidence

_CHUNK_SIZE = 1024 * 1024  # 1 MB


class StorageService:
    """Handles physical evidence storage.

    Original files are stored read-only under `storage/evidence/originals/`
    and are never overwritten. Analysis operates on working copies under
    `storage/evidence/processed/`.
    """

    @property
    def originals_dir(self) -> Path:
        return settings.storage_originals_dir

    @property
    def processed_dir(self) -> Path:
        return settings.storage_processed_dir

    @property
    def quarantine_dir(self) -> Path:
        return settings.storage_quarantine_dir

    def store_original(
        self,
        source_file,
        case_id: str,
        stored_filename: str,
        *,
        max_size: int,
    ) -> dict:
        """Write an original evidence file, refuse to overwrite, and make it read-only."""
        case_dir = self.originals_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        destination = case_dir / stored_filename
        if destination.exists():
            raise StorageError("Refusing to overwrite an existing evidence file")

        source_file.seek(0)
        try:
            size = self._copy_with_limit(source_file, destination, max_size)
        except AppError:
            destination.unlink(missing_ok=True)
            raise

        self._make_readonly(destination)
        return {"storage_path": str(destination), "file_size": size}

    def quarantine(self, source_file, *, reason: str) -> Path:
        """Retain a rejected file for later review (never executed)."""
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        destination = self.quarantine_dir / f"{uuid.uuid4().hex}.bin"
        source_file.seek(0)
        with destination.open("wb") as out:
            shutil.copyfileobj(source_file, out, _CHUNK_SIZE)
        return destination

    def create_working_copy(self, evidence: Evidence) -> Path:
        """Copy an original evidence file to the processed area for analysis."""
        source = Path(evidence.storage_path)
        if not source.exists():
            raise StorageError("Evidence source file is missing")
        dest_dir = self.processed_dir / str(evidence.id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        destination = dest_dir / evidence.stored_filename
        shutil.copyfile(source, destination)
        return destination

    @staticmethod
    def _copy_with_limit(source, destination: Path, max_size: int) -> int:
        total = 0
        with destination.open("wb") as out:
            while True:
                chunk = source.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise AppError("File exceeds the maximum allowed upload size", status_code=413)
                out.write(chunk)
        return total

    @staticmethod
    def _make_readonly(path: Path) -> None:
        """Remove write access from an evidence file (works on Windows)."""
        path.chmod(stat.S_IREAD)
