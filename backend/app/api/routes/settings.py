"""
Application settings endpoints.
"""
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.schemas import (
    SettingsResponse,
    SettingsUpdate,
    SuccessResponse
)
from app.core.dependencies import get_db, get_settings, get_stash_service
from app.core.config import Settings
from app.models import Setting
from app.services.stash_service import StashService
import openai

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_settings(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get all application settings.
    """
    # Load settings from database
    query = select(Setting)
    result = await db.execute(query)
    db_settings = result.scalars().all()
    
    # Build settings dict with database overrides
    settings_dict = {
        "stash_url": settings.STASH_URL,
        "stash_configured": bool(settings.STASH_URL and settings.STASH_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "analysis_confidence_threshold": 0.7,
        "sync_incremental": True,
        "sync_batch_size": 100
    }
    
    # Apply database overrides
    for setting in db_settings:
        if setting.key in ["stash_api_key", "openai_api_key"]:
            # Mask sensitive values
            settings_dict[setting.key] = "*" * 8 if setting.value else None
        else:
            settings_dict[setting.key] = setting.value
    
    return settings_dict


@router.put("/")
async def update_settings(
    settings_update: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update application settings.
    """
    updated_fields = []
    
    # Validate setting keys
    allowed_keys = {
        "stash_url", "stash_api_key", "openai_api_key", "openai_model",
        "analysis_confidence_threshold", "sync_incremental", "sync_batch_size"
    }
    
    for key, value in settings_update.items():
        if key not in allowed_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown setting key: {key}"
            )
        
        # Check if setting exists
        query = select(Setting).where(Setting.key == key)
        result = await db.execute(query)
        setting = result.scalar_one_or_none()
        
        if setting:
            # Update existing setting
            setting.value = value
        else:
            # Create new setting
            setting = Setting(key=key, value=value)
            db.add(setting)
        
        updated_fields.append(key)
    
    await db.commit()
    
    # Determine if restart is needed
    requires_restart = any(key in ["stash_url", "stash_api_key"] for key in updated_fields)
    
    return {
        "success": True,
        "message": "Settings updated successfully",
        "updated_fields": updated_fields,
        "requires_restart": requires_restart
    }


@router.post("/test-stash")
async def test_stash_connection(
    url: Optional[str] = Body(None, description="Stash URL to test"),
    api_key: Optional[str] = Body(None, description="API key to test"),
    stash_service: StashService = Depends(get_stash_service),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Test Stash connection.
    """
    try:
        # Use provided credentials or defaults
        test_url = url or settings.STASH_URL
        test_key = api_key or settings.STASH_API_KEY
        
        if not test_url:
            raise ValueError("No Stash URL configured")
        
        # Test connection
        result = await stash_service.test_connection(
            url=test_url,
            api_key=test_key
        )
        
        return {
            "service": "stash",
            "success": True,
            "message": "Successfully connected to Stash server",
            "details": {
                "server_version": result.get("version", "unknown"),
                "scene_count": result.get("scene_count", 0),
                "performer_count": result.get("performer_count", 0)
            }
        }
    except Exception as e:
        return {
            "service": "stash",
            "success": False,
            "message": f"Failed to connect to Stash: {str(e)}",
            "details": {
                "error": str(e),
                "url_tested": url or settings.STASH_URL
            }
        }


@router.post("/test-openai")
async def test_openai_connection(
    api_key: Optional[str] = Body(None, description="API key to test"),
    model: Optional[str] = Body(None, description="Model to test"),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Test OpenAI connection.
    """
    try:
        # Use provided credentials or defaults
        test_key = api_key or settings.OPENAI_API_KEY
        test_model = model or settings.OPENAI_MODEL
        
        if not test_key:
            raise ValueError("No OpenAI API key configured")
        
        # Test connection with a simple API call
        openai.api_key = test_key
        
        # List available models
        models = openai.models.list()
        model_ids = [m.id for m in models.data]
        
        # Check if specified model is available
        if test_model not in model_ids:
            raise ValueError(f"Model {test_model} not available")
        
        return {
            "service": "openai",
            "success": True,
            "message": "Successfully connected to OpenAI API",
            "details": {
                "model": test_model,
                "available_models": model_ids[:10],  # First 10 models
                "total_models": len(model_ids)
            }
        }
    except Exception as e:
        return {
            "service": "openai",
            "success": False,
            "message": f"Failed to connect to OpenAI: {str(e)}",
            "details": {
                "error": str(e),
                "model_attempted": model or settings.OPENAI_MODEL
            }
        }