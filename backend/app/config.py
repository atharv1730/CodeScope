"""Application configuration, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://repolens:repolens@localhost:5432/repolens"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Cloning / analysis guard rails
    clone_dir: str = "/tmp/repolens_clones"
    clone_timeout_seconds: int = 120
    max_repo_size_mb: int = 500
    analysis_cache_ttl_seconds: int = 3600

    # CORS (comma-separated string -> list)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        # We store analysis data in Postgres; Redis backend is only used for
        # task bookkeeping, never as the source of truth for results.
        return self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
