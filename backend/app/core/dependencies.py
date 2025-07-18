"""
Dependency injection functions for FastAPI.
"""

from collections.abc import AsyncGenerator
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionLocal
from app.models import Setting
from app.services.analysis.analysis_service import AnalysisService
from app.services.job_service import JobService
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService
from app.services.sync.sync_service import SyncService
from app.services.websocket_manager import get_websocket_manager  # noqa: F401

__all__ = [
    "get_db",
    "get_settings",
    "get_stash_client",
    "get_openai_client",
    "get_current_user",
    "require_auth",
    "get_stash_service",
    "get_sync_service",
    "get_analysis_service",
    "get_job_service",
    "get_websocket_manager",
    "PaginationParams",
    "StashClient",
    "Settings",
]

# Re-export for backward compatibility
StashClient = StashService  # Alias for backward compatibility

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def _get_base_settings_dict(base_settings: Settings) -> dict[str, dict[str, Any]]:
    """Create base settings dictionary from settings object."""
    return {
        "stash": {
            "url": base_settings.stash.url,
            "api_key": base_settings.stash.api_key,
            "timeout": base_settings.stash.timeout,
            "max_retries": base_settings.stash.max_retries,
        },
        "openai": {
            "api_key": base_settings.openai.api_key,
            "model": base_settings.openai.model,
            "max_tokens": base_settings.openai.max_tokens,
            "temperature": base_settings.openai.temperature,
            "timeout": base_settings.openai.timeout,
        },
        "analysis": {
            "batch_size": base_settings.analysis.batch_size,
            "max_concurrent": base_settings.analysis.max_concurrent,
            "confidence_threshold": base_settings.analysis.confidence_threshold,
            "enable_ai": base_settings.analysis.enable_ai,
            "create_missing": base_settings.analysis.create_missing,
            "ai_video_server_url": base_settings.analysis.ai_video_server_url,
            "frame_interval": base_settings.analysis.frame_interval,
            "ai_video_threshold": base_settings.analysis.ai_video_threshold,
            "server_timeout": base_settings.analysis.server_timeout,
            "create_markers": base_settings.analysis.create_markers,
        },
    }


def _apply_setting_override(
    settings_dict: dict[str, dict[str, Any]], key: str, value: Optional[str]
) -> None:
    """Apply a single setting override to the settings dictionary."""
    if value is None:
        return

    # Define mapping of setting keys to their locations and transformations
    mapping = {
        "stash_url": ("stash", "url", str),
        "stash_api_key": ("stash", "api_key", str),
        "openai_api_key": ("openai", "api_key", str),
        "openai_model": ("openai", "model", str),
        "openai_base_url": ("openai", "base_url", str),
        "analysis_confidence_threshold": ("analysis", "confidence_threshold", float),
        "video_ai_server_url": ("analysis", "ai_video_server_url", str),
        "video_ai_frame_interval": ("analysis", "frame_interval", int),
        "video_ai_threshold": ("analysis", "ai_video_threshold", float),
        "video_ai_timeout": ("analysis", "server_timeout", int),
        "video_ai_create_markers": ("analysis", "create_markers", bool),
    }

    if key in mapping:
        section, field, transform = mapping[key]
        try:
            settings_dict[section][field] = transform(value)
        except (ValueError, TypeError):
            pass  # Ignore conversion errors


async def get_settings_with_overrides(
    db: AsyncSession = Depends(get_db),
    base_settings: Settings = Depends(get_settings),
) -> Settings:
    """
    Get settings with database overrides.

    Database settings take precedence over environment variables.
    If a setting is not in the database, fall back to environment variable.

    Args:
        db: Database session
        base_settings: Base settings from environment

    Returns:
        Settings: Settings with database overrides applied
    """
    # Query all settings from database
    result = await db.execute(select(Setting))
    db_settings = result.scalars().all()

    # Create a copy of base settings
    settings_dict = _get_base_settings_dict(base_settings)

    # Apply database overrides
    for setting in db_settings:
        _apply_setting_override(settings_dict, setting.key, setting.value)  # type: ignore[arg-type]

    # Create new settings instance with overrides
    from app.core.config import AnalysisSettings, OpenAISettings, StashSettings

    overridden_settings = Settings(
        app=base_settings.app,
        database=base_settings.database,
        stash=StashSettings(**settings_dict["stash"]),
        openai=OpenAISettings(**settings_dict["openai"]),
        analysis=AnalysisSettings(**settings_dict["analysis"]),
        security=base_settings.security,
        cors=base_settings.cors,
        logging=base_settings.logging,
        redis_url=base_settings.redis_url,
        max_workers=base_settings.max_workers,
        task_timeout=base_settings.task_timeout,
    )

    return overridden_settings


def get_stash_client(
    settings: Settings = Depends(get_settings_with_overrides),
) -> StashClient:
    """
    Get Stash API client instance.

    Args:
        settings: Application settings

    Returns:
        StashService: Stash API client
    """
    return StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries,
    )


def get_openai_client(
    settings: Settings = Depends(get_settings_with_overrides),
) -> Optional[OpenAIClient]:
    """
    Get OpenAI client instance.

    Args:
        settings: Application settings

    Returns:
        Optional[OpenAIClient]: OpenAI client if API key is configured
    """
    if not settings.openai.api_key:
        return None

    return OpenAIClient(
        api_key=settings.openai.api_key,
        model=settings.openai.model,
        base_url=settings.openai.base_url,
        max_tokens=settings.openai.max_tokens,
        temperature=settings.openai.temperature,
        timeout=settings.openai.timeout,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings_with_overrides),
) -> Optional[dict]:
    """
    Get current authenticated user (optional).

    This is a placeholder for future authentication implementation.
    Currently returns None to allow unauthenticated access.

    Args:
        credentials: Bearer token credentials
        settings: Application settings

    Returns:
        Optional[dict]: User information if authenticated
    """
    # For now, authentication is optional
    # In the future, this can validate JWT tokens
    return None


async def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """
    Require authenticated user.

    Args:
        user: Current user from get_current_user

    Returns:
        dict: User information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


class PaginationParams:
    """Common pagination parameters."""

    def __init__(self, page: int = 1, size: int = 20, sort: Optional[str] = None):
        """
        Initialize pagination parameters.

        Args:
            page: Page number (1-based)
            size: Page size
            sort: Sort field and direction (e.g., "-created_at")
        """
        self.page = max(1, page)
        self.size = min(100, max(1, size))  # Limit max size to 100
        self.sort = sort

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size


def get_stash_service(
    settings: Settings = Depends(get_settings_with_overrides),
) -> StashService:
    """
    Get Stash service instance.

    Returns:
        StashService: Stash service instance
    """
    return StashService(stash_url=settings.stash.url, api_key=settings.stash.api_key)


async def get_sync_service(
    stash_service: StashService = Depends(get_stash_service),
    db: AsyncSession = Depends(get_db),
) -> SyncService:
    """
    Get Sync service instance.

    Args:
        stash_service: Stash service
        db: Async database session

    Returns:
        SyncService: Sync service instance
    """
    return SyncService(stash_service=stash_service, db_session=db)


def get_analysis_service(
    openai_client: Optional[OpenAIClient] = Depends(get_openai_client),
    stash_service: StashService = Depends(get_stash_service),
    settings: Settings = Depends(get_settings_with_overrides),
) -> AnalysisService:
    """
    Get Analysis service instance.

    Args:
        openai_client: OpenAI client
        stash_service: Stash service
        settings: Application settings

    Returns:
        AnalysisService: Analysis service
    """
    if openai_client is None:
        raise ValueError("OpenAI client is required for analysis service")
    return AnalysisService(
        openai_client=openai_client, stash_service=stash_service, settings=settings
    )


def get_job_service() -> JobService:
    """
    Get Job service instance.

    Returns:
        JobService: Job service
    """
    from app.services.job_service import job_service

    return job_service
