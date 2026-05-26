"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Book-IA"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    fernet_key: str = ""

    @property
    def fernet_encryption_key(self) -> bytes:
        """Return a Fernet-compatible key (32 url-safe base64 bytes)."""
        import base64
        import hashlib

        if self.fernet_key:
            return self.fernet_key.encode()
        digest = hashlib.sha256(self.secret_key.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    # --- Session / Auth ---
    session_cookie_name: str = "bookia_session"
    session_idle_timeout_minutes: int = 30
    bcrypt_rounds: int = 12
    cookie_secure: bool = False

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:8000"]

    # --- Database ---
    database_url: str = "postgresql+asyncpg://bookia:bookia@localhost:5432/bookia"
    database_sync_url: str = "postgresql://bookia:bookia@localhost:5432/bookia"

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    # Empty = PostgreSQL via database_sync_url (db+...). Set redis://... to use Redis.
    celery_result_backend: str = ""

    @property
    def celery_backend_url(self) -> str:
        """Resolved Celery result backend (PostgreSQL db+ or explicit Redis URL)."""
        if self.celery_result_backend:
            return self.celery_result_backend
        return f"db+{self.database_sync_url}"

    # --- External APIs ---
    tts_api_url: str = "http://localhost:8001"
    musicgen_api_url: str = "http://localhost:8002"
    llm_cloud_api_url: str = "https://generativelanguage.googleapis.com"
    llm_local_api_url: str = "http://192.168.2.183:11434"
    llm_cloud_api_key: str = ""

    # --- Timeouts (seconds) ---
    llm_timeout: int = 60
    tts_timeout: int = 120
    musicgen_timeout: int = 180

    # --- File storage ---
    pdfs_dir: str = "./storage/pdfs"
    audio_dir: str = "./storage/audio"
    max_upload_size_mb: int = 50

    # --- Celery ---
    celery_max_retries: int = 3
    celery_task_time_limit: int = 3600
    celery_task_soft_time_limit: int = 3000

    @field_validator("database_url", mode="before")
    @classmethod
    def prepare_async_url(cls, v: str) -> str:
        """Convert sync SQLAlchemy URL to asyncpg-compatible URL."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
