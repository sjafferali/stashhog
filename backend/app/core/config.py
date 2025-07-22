"""
Application configuration and settings management.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-specific settings."""

    name: str = Field("StashHog", description="Application name")
    version: str = Field("0.1.0", description="Application version")
    debug: bool = Field(False, description="Debug mode")
    environment: str = Field(
        "production", description="Environment (development, staging, production)"
    )

    model_config = SettingsConfigDict(env_prefix="APP_")


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field("sqlite:///./stashhog.db", description="Database connection URL")
    echo: bool = Field(False, description="Echo SQL statements")
    pool_size: int = Field(10, description="Connection pool size")
    pool_recycle: int = Field(
        3600, description="Connection pool recycle time in seconds"
    )

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is properly formatted."""
        if not v:
            raise ValueError("Database URL cannot be empty")
        return v


class StashSettings(BaseSettings):
    """Stash API configuration settings."""

    url: str = Field("http://localhost:9999", description="Stash server URL")
    api_key: Optional[str] = Field(None, description="Stash API key")
    timeout: int = Field(30, description="API request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")

    model_config = SettingsConfigDict(env_prefix="STASH_")

    @field_validator("url")
    @classmethod
    def validate_stash_url(cls, v: str) -> str:
        """Ensure Stash URL is properly formatted."""
        if not v:
            raise ValueError("Stash URL cannot be empty")
        # Remove trailing slash for consistency
        return v.rstrip("/")


class OpenAISettings(BaseSettings):
    """OpenAI configuration settings."""

    api_key: Optional[str] = Field(None, description="OpenAI API key")
    model: str = Field("gpt-4", description="Model to use")
    base_url: Optional[str] = Field(
        None, description="Custom API endpoint for OpenAI-compatible services"
    )
    max_tokens: int = Field(2000, description="Maximum tokens per request")
    temperature: float = Field(0.7, description="Temperature for generation")
    timeout: int = Field(60, description="API request timeout in seconds")

    model_config = SettingsConfigDict(env_prefix="OPENAI_")


class SecuritySettings(BaseSettings):
    """Security-related settings."""

    secret_key: str = Field(
        "change-this-in-production-to-a-random-string",
        description="Secret key for signing",
    )
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        30, description="Access token expiration time"
    )

    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class CORSSettings(BaseSettings):
    """CORS configuration settings."""

    origins: list[str] = Field(
        ["*"],
        description="Allowed origins",
    )
    credentials: bool = Field(True, description="Allow credentials")
    methods: list[str] = Field(["*"], description="Allowed methods")
    headers: list[str] = Field(["*"], description="Allowed headers")

    model_config = SettingsConfigDict(env_prefix="CORS_")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format"
    )
    json_logs: bool = Field(False, description="Use JSON logging format")

    model_config = SettingsConfigDict(env_prefix="LOGGING_")


class AnalysisSettings(BaseSettings):
    """Analysis service configuration settings."""

    batch_size: int = Field(
        15, description="Number of scenes per batch for AI analysis"
    )
    max_concurrent: int = Field(3, description="Maximum concurrent analysis batches")
    confidence_threshold: float = Field(0.7, description="Default confidence threshold")
    enable_ai: bool = Field(True, description="Enable AI-based detection")
    create_missing: bool = Field(
        False, description="Create missing entities during analysis"
    )

    # Video AI server settings
    ai_video_server_url: str = Field(
        "http://localhost:8084", description="External AI video processing server URL"
    )
    frame_interval: int = Field(
        2, description="Frame extraction interval in seconds for video analysis"
    )
    ai_video_threshold: float = Field(
        0.3, description="Confidence threshold for video AI detection"
    )
    server_timeout: int = Field(
        3700, description="Timeout for video processing requests in seconds"
    )
    create_markers: bool = Field(
        True, description="Create scene markers from video AI detection"
    )

    model_config = SettingsConfigDict(env_prefix="ANALYSIS_")


class Settings(BaseSettings):
    """Main settings class combining all configuration sections."""

    # Sub-settings
    app: AppSettings = Field(default_factory=lambda: AppSettings())  # type: ignore[call-arg]
    database: DatabaseSettings = Field(default_factory=lambda: DatabaseSettings())  # type: ignore[call-arg]
    stash: StashSettings = Field(default_factory=lambda: StashSettings())  # type: ignore[call-arg]
    openai: OpenAISettings = Field(default_factory=lambda: OpenAISettings())  # type: ignore[call-arg]
    security: SecuritySettings = Field(default_factory=lambda: SecuritySettings())  # type: ignore[call-arg]
    cors: CORSSettings = Field(default_factory=lambda: CORSSettings())  # type: ignore[call-arg]
    logging: LoggingSettings = Field(default_factory=lambda: LoggingSettings())  # type: ignore[call-arg]
    analysis: AnalysisSettings = Field(default_factory=lambda: AnalysisSettings())  # type: ignore[call-arg]

    # Redis settings (optional, for future use)
    redis_url: Optional[str] = Field(None, description="Redis connection URL")

    # Task queue settings
    max_workers: int = Field(5, description="Maximum number of background workers")
    task_timeout: int = Field(300, description="Task timeout in seconds")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings(redis_url=None, max_workers=5, task_timeout=300)
