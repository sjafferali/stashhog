"""
Application settings endpoints.
"""

from typing import Any, Dict, List, Optional

import openai
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import (
    get_db,
    get_settings,
    get_settings_with_overrides,
    get_stash_service,
)
from app.models import Setting
from app.services.stash_service import StashService

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    base_settings: Settings = Depends(get_settings),
    overridden_settings: Settings = Depends(get_settings_with_overrides),
) -> List[Dict[str, Any]]:
    """
    Get all application settings with source information.
    """
    # Load settings from database
    query = select(Setting)
    result = await db.execute(query)
    db_settings = result.scalars().all()

    # Create a map of database settings
    db_settings_map = {s.key: s.value for s in db_settings}

    # Define settings to expose
    settings_config = [
        (
            "stash_url",
            "stash.url",
            base_settings.stash.url,
            overridden_settings.stash.url,
            "Stash URL",
            False,
        ),
        (
            "stash_api_key",
            "stash.api_key",
            base_settings.stash.api_key,
            overridden_settings.stash.api_key,
            "Stash API key",
            True,
        ),
        (
            "openai_api_key",
            "openai.api_key",
            base_settings.openai.api_key,
            overridden_settings.openai.api_key,
            "OpenAI API key",
            True,
        ),
        (
            "openai_model",
            "openai.model",
            base_settings.openai.model,
            overridden_settings.openai.model,
            "OpenAI model",
            False,
        ),
        (
            "analysis_confidence_threshold",
            "analysis.confidence_threshold",
            base_settings.analysis.confidence_threshold,
            overridden_settings.analysis.confidence_threshold,
            "Analysis confidence threshold",
            False,
        ),
        (
            "sync_incremental",
            "sync.incremental",
            True,
            db_settings_map.get("sync_incremental", True),
            "Enable incremental sync",
            False,
        ),
        (
            "sync_batch_size",
            "sync.batch_size",
            100,
            db_settings_map.get("sync_batch_size", 100),
            "Sync batch size",
            False,
        ),
    ]

    settings_list: List[Dict[str, Any]] = []

    for (
        key,
        display_key,
        env_value,
        current_value,
        description,
        is_secret,
    ) in settings_config:
        # Determine source
        if key in db_settings_map:
            source = "database"
            db_value = db_settings_map[key]
        else:
            source = "environment"
            db_value = None

        # Handle secret masking
        display_value = current_value
        if is_secret and current_value:
            display_value = "********"

        env_display_value = env_value
        if is_secret and env_value:
            env_display_value = "********"

        settings_list.append(
            {
                "key": display_key,
                "value": display_value,
                "description": description,
                "source": source,
                "env_value": env_display_value,
                "db_value": "********" if is_secret and db_value else db_value,
                "editable": True,
            }
        )

    # Add read-only settings
    readonly_settings = [
        ("app.name", base_settings.app.name, "Application name"),
        ("app.version", base_settings.app.version, "Application version"),
    ]

    for key, value, description in readonly_settings:
        settings_list.append(
            {
                "key": key,
                "value": value,
                "description": description,
                "source": "config",
                "editable": False,
            }
        )

    return settings_list


@router.get("/{key}")
async def get_setting(key: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a specific setting by key.
    """
    query = select(Setting).where(Setting.key == key)
    result = await db.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting not found: {key}"
        )

    return {
        "key": setting.key,
        "value": setting.value,
        "description": setting.description,
    }


@router.put("/{key}")
async def update_setting(
    key: str, update: Any = Body(...), db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update a specific setting by key.
    """
    query = select(Setting).where(Setting.key == key)
    result = await db.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        # Create new setting
        value = update.get("value") if isinstance(update, dict) else update
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        # Update existing setting
        value = update.get("value") if isinstance(update, dict) else update
        setting.value = value

    await db.commit()

    return {
        "success": True,
        "message": f"Setting '{key}' updated successfully",
        "key": key,
        "value": setting.value,
    }


@router.put("")
async def update_settings(
    settings_update: Dict[str, Any], db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update application settings.

    Setting a value to null or empty string will delete it from database,
    causing the system to use the environment variable default.
    """
    updated_fields = []
    deleted_fields = []

    # Validate setting keys
    allowed_keys = {
        "stash_url",
        "stash_api_key",
        "openai_api_key",
        "openai_model",
        "analysis_confidence_threshold",
        "sync_incremental",
        "sync_batch_size",
    }

    for key, value in settings_update.items():
        if key not in allowed_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown setting key: {key}",
            )

        # Check if setting exists
        query = select(Setting).where(Setting.key == key)
        result = await db.execute(query)
        setting = result.scalar_one_or_none()

        # Handle deletion (null or empty string)
        if value is None or value == "":
            if setting:
                await db.delete(setting)
                deleted_fields.append(key)
        else:
            if setting:
                # Update existing setting
                setting.value = value
                updated_fields.append(key)
            else:
                # Create new setting
                setting = Setting(key=key, value=value)
                db.add(setting)
                updated_fields.append(key)

    await db.commit()

    # Determine if restart is needed
    requires_restart = any(
        key in ["stash_url", "stash_api_key"] for key in updated_fields + deleted_fields
    )

    return {
        "success": True,
        "message": "Settings updated successfully",
        "updated_fields": updated_fields,
        "deleted_fields": deleted_fields,
        "requires_restart": requires_restart,
    }


@router.post("/test-stash")
async def test_stash_connection(
    url: Optional[str] = Body(None, description="Stash URL to test"),
    api_key: Optional[str] = Body(None, description="API key to test"),
    stash_service: StashService = Depends(get_stash_service),
    settings: Settings = Depends(get_settings_with_overrides),
) -> Dict[str, Any]:
    """
    Test Stash connection.
    """
    try:
        # Use provided credentials or defaults
        test_url = url or settings.stash.url
        test_key = api_key or settings.stash.api_key

        if not test_url:
            raise ValueError("No Stash URL configured")

        # Test connection - create temporary client with test credentials
        from app.services.stash_service import StashService

        test_service = StashService(stash_url=test_url, api_key=test_key)
        result = await test_service.test_connection()

        return {
            "service": "stash",
            "success": result,
            "message": (
                "Successfully connected to Stash server"
                if result
                else "Failed to connect"
            ),
            "details": {
                "server_version": "unknown",
                "scene_count": 0,
                "performer_count": 0,
            },
        }
    except Exception as e:
        return {
            "service": "stash",
            "success": False,
            "message": f"Failed to connect to Stash: {str(e)}",
            "details": {"error": str(e), "url_tested": url or settings.stash.url},
        }


@router.post("/test-openai")
async def test_openai_connection(
    api_key: Optional[str] = Body(None, description="API key to test"),
    model: Optional[str] = Body(None, description="Model to test"),
    settings: Settings = Depends(get_settings_with_overrides),
) -> Dict[str, Any]:
    """
    Test OpenAI connection.
    """
    try:
        # Use provided credentials or defaults
        test_key = api_key or settings.openai.api_key
        test_model = model or settings.openai.model

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
                "total_models": len(model_ids),
            },
        }
    except Exception as e:
        return {
            "service": "openai",
            "success": False,
            "message": f"Failed to connect to OpenAI: {str(e)}",
            "details": {
                "error": str(e),
                "model_attempted": model or settings.openai.model,
            },
        }
