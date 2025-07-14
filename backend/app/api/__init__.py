"""
API router aggregation.
"""
from fastapi import APIRouter

from app.api.routes import health, scenes, analysis, jobs, settings, sync, entities

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])

__all__ = ["api_router"]