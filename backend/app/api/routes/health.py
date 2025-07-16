"""
Health check endpoints.
"""

from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import (
    get_db,
    get_openai_client,
    get_settings,
    get_stash_client,
)
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService

router = APIRouter()


@router.get("", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Dict with health status
    """
    return {"status": "healthy"}


async def _check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        return {"status": "ready", "error": None}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


async def _check_stash(stash_client: StashService) -> Dict[str, Any]:
    """Check Stash service connectivity."""
    try:
        result = await stash_client.test_connection()
        if result:
            return {"status": "ready", "error": None}
        else:
            return {"status": "not ready", "error": "Connection test failed"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


async def _check_openai(openai_client: OpenAIClient) -> Dict[str, Any]:
    """Check OpenAI service connectivity."""
    if not openai_client:
        return {"status": "not configured", "error": None}
    try:
        result = await openai_client.test_connection()
        if result:
            return {"status": "ready", "error": None}
        else:
            return {"status": "not ready", "error": "Connection test failed"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    stash_client: StashService = Depends(get_stash_client),
    openai_client: OpenAIClient = Depends(get_openai_client),
    settings: Settings = Depends(get_settings),
) -> Union[Dict[str, Any], JSONResponse]:
    """
    Comprehensive readiness check.

    Checks if all services are ready to handle requests.

    Returns:
        Dict with readiness status and individual service checks
    """
    checks = {
        "database": await _check_database(db),
        "stash": await _check_stash(stash_client),
        "openai": await _check_openai(openai_client),
    }

    # Determine overall readiness
    critical_services = ["database", "stash"]
    all_ready = all(
        checks[service]["status"] == "ready" for service in critical_services
    )

    response = {"status": "ready" if all_ready else "not ready", "checks": checks}

    # Return appropriate status code
    if not all_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response
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
            "authentication": bool(
                settings.security.secret_key != "your-secret-key-here"
            ),
        },
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
