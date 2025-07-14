"""
Health check endpoints.
"""
from typing import Dict, Any
import asyncio

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_stash_client, get_openai_client, get_settings
from app.core.config import Settings
from app.services.stash_client import StashClient
from app.services.openai_client import OpenAIClient

router = APIRouter()


@router.get("/", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict with health status
    """
    return {"status": "healthy"}


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    stash_client: StashClient = Depends(get_stash_client),
    openai_client: OpenAIClient = Depends(get_openai_client),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Comprehensive readiness check.
    
    Checks if all services are ready to handle requests.
    
    Returns:
        Dict with readiness status and individual service checks
    """
    checks = {
        "database": {"status": "unknown", "error": None},
        "stash": {"status": "unknown", "error": None},
        "openai": {"status": "unknown", "error": None},
    }
    
    # Check database
    try:
        # Execute a simple query
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        checks["database"]["status"] = "ready"
    except Exception as e:
        checks["database"]["status"] = "not ready"
        checks["database"]["error"] = str(e)
    
    # Check Stash connection
    try:
        if await stash_client.test_connection():
            checks["stash"]["status"] = "ready"
        else:
            checks["stash"]["status"] = "not ready"
            checks["stash"]["error"] = "Connection test failed"
    except Exception as e:
        checks["stash"]["status"] = "not ready"
        checks["stash"]["error"] = str(e)
    
    # Check OpenAI connection (only if configured)
    if openai_client:
        try:
            if await openai_client.test_connection():
                checks["openai"]["status"] = "ready"
            else:
                checks["openai"]["status"] = "not ready"
                checks["openai"]["error"] = "Connection test failed"
        except Exception as e:
            checks["openai"]["status"] = "not ready"
            checks["openai"]["error"] = str(e)
    else:
        checks["openai"]["status"] = "not configured"
    
    # Determine overall readiness
    critical_services = ["database", "stash"]
    all_ready = all(
        checks[service]["status"] == "ready" 
        for service in critical_services
    )
    
    response = {
        "status": "ready" if all_ready else "not ready",
        "checks": checks
    }
    
    # Return appropriate status code
    if not all_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )
    
    return response


@router.get("/version", response_model=Dict[str, Any])
async def version_info(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Get application version and build information.
    
    Returns:
        Dict with version information
    """
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "environment": settings.app.environment,
        "debug": settings.app.debug,
        "features": {
            "stash": bool(settings.stash.url),
            "openai": bool(settings.openai.api_key),
            "authentication": bool(settings.security.secret_key != "your-secret-key-here"),
        }
    }


@router.get("/ping", response_model=Dict[str, float])
async def ping() -> Dict[str, float]:
    """
    Simple ping endpoint for latency checks.
    
    Returns:
        Dict with timestamp
    """
    import time
    return {"timestamp": time.time()}