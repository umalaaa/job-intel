from typing import Any, Dict, List, Optional
from pydantic import AnyHttpUrl, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Job Intel"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./job-intel.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API Keys
    TAVILY_API_KEY: Optional[str] = None

    # Resource Thresholds
    RESOURCE_DISK_MIN_FREE_PERCENT: float = 15.0
    RESOURCE_CPU_MAX_PERCENT: float = 85.0

    # Data Retention
    RETENTION_EXPIRED_DAYS: int = 30
    RETENTION_ARCHIVE_DAYS: int = 90

    # Scraper Settings
    TAVILY_MAX_RESULTS: int = 25
    TAVILY_SEARCH_DEPTH: str = "basic"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
