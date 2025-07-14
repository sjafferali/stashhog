"""
Dependency injection functions for FastAPI.
"""
from typing import AsyncGenerator, Optional
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionLocal, SessionLocal
from app.services.stash_service import StashClient, StashService
from app.services.openai_client import OpenAIClient
from app.services.sync_service import SyncService
from app.services.analysis_service import AnalysisService
from app.services.job_queue import JobQueue, get_job_queue
from app.services.websocket_manager import WebSocketManager, get_websocket_manager


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


@lru_cache()
def get_stash_client(settings: Settings = Depends(get_settings)) -> StashClient:
    """
    Get Stash API client instance.
    
    Args:
        settings: Application settings
        
    Returns:
        StashClient: Stash API client
    """
    return StashClient(
        base_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries
    )


@lru_cache()
def get_openai_client(settings: Settings = Depends(get_settings)) -> Optional[OpenAIClient]:
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
        max_tokens=settings.openai.max_tokens,
        temperature=settings.openai.temperature,
        timeout=settings.openai.timeout
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
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


async def require_auth(
    user: Optional[dict] = Depends(get_current_user)
) -> dict:
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
    
    def __init__(
        self,
        page: int = 1,
        size: int = 20,
        sort: Optional[str] = None
    ):
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


def get_stash_service(settings: Settings = Depends(get_settings)) -> StashService:
    """
    Get Stash service instance.
    
    Returns:
        StashService: Stash service instance
    """
    return StashService(
        url=settings.stash.url,
        api_key=settings.stash.api_key
    )


async def get_sync_service(
    db: AsyncSession = Depends(get_db),
    stash_service: StashService = Depends(get_stash_service)
) -> SyncService:
    """
    Get Sync service instance.
    
    Args:
        db: Database session
        stash_service: Stash service
        
    Returns:
        SyncService: Sync service instance
    """
    return SyncService(stash_service=stash_service, db=db)


async def get_analysis_service(
    db: AsyncSession = Depends(get_db),
    openai_client: Optional[OpenAIClient] = Depends(get_openai_client),
    stash_service: StashService = Depends(get_stash_service),
    settings: Settings = Depends(get_settings)
) -> AnalysisService:
    """
    Get Analysis service instance.
    
    Args:
        db: Database session
        openai_client: OpenAI client
        stash_service: Stash service
        settings: Application settings
        
    Returns:
        AnalysisService: Analysis service
    """
    return AnalysisService(
        db=db,
        openai_client=openai_client,
        stash_service=stash_service
    )