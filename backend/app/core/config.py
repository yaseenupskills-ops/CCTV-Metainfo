from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "CCTV Forensic Analyzer"
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str = ""

    # Database
    database_url: str = "postgresql+psycopg://cctv_user:change_me@localhost:5432/cctv_forensics"

    # Security
    jwt_secret: str = "change_me_generate_a_long_random_string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Storage
    storage_path: Path = Path("./storage")
    max_upload_size: int = 5 * 1024 * 1024 * 1024  # 5 GB in bytes
    allowed_extensions: list[str] = [".mp4", ".mov", ".avi", ".mkv"]

    # FFmpeg / FFprobe
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # Background workers (used from Phase 16)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = True

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Frame analysis defaults
    frame_sampling_rates: list[int] = [1, 2, 5]
    default_frame_sampling_rate: int = 1
    scene_diff_threshold: float = 0.35

    # Rate limiting
    login_rate_limit: str = "5/minute"

    # Request hardening
    max_request_body_size: int = 1024 * 1024  # 1 MB for JSON bodies

    # Derived storage paths
    @property
    def storage_originals_dir(self) -> Path:
        return self.storage_path / "evidence" / "originals"

    @property
    def storage_processed_dir(self) -> Path:
        return self.storage_path / "evidence" / "processed"

    @property
    def storage_quarantine_dir(self) -> Path:
        return self.storage_path / "evidence" / "quarantine"

    @property
    def storage_reports_dir(self) -> Path:
        return self.storage_path / "reports"

    def ensure_storage_dirs(self) -> None:
        for directory in (
            self.storage_originals_dir,
            self.storage_processed_dir,
            self.storage_quarantine_dir,
            self.storage_reports_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
