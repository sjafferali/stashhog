"""Settings loader utility for background jobs."""

from typing import Any, Dict

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionLocal
from app.models.setting import Setting


def _parse_db_settings(db_settings) -> Dict[str, Any]:
    """Parse database settings into a nested dictionary structure."""
    overrides: Dict[str, Any] = {}

    for setting in db_settings:
        # Convert database key format (e.g., "stash_url") to nested format
        key_parts = setting.key.split("_", 1)
        if len(key_parts) == 2:
            section, key = key_parts
            if section not in overrides:
                overrides[section] = {}
            overrides[section][key] = setting.value
        else:
            # Handle non-nested keys
            overrides[setting.key] = setting.value

    return overrides


def _apply_section_overrides(
    settings_dict: Dict[str, Any], overrides: Dict[str, Any], section: str
):
    """Apply overrides for a specific section."""
    if section not in overrides:
        return

    for key, value in overrides[section].items():
        if key in settings_dict.get(section, {}):
            settings_dict[section][key] = value


def _apply_stash_overrides(settings_dict: Dict[str, Any], overrides: Dict[str, Any]):
    """Apply stash-specific overrides with special handling."""
    if "stash" not in overrides:
        return

    if "url" in overrides["stash"]:
        settings_dict["stash"]["url"] = overrides["stash"]["url"]

    if "api_key" in overrides["stash"]:
        # Handle None/null values for api_key
        value = overrides["stash"]["api_key"]
        if value is not None and value != 0:  # Skip 0 values (data error)
            settings_dict["stash"]["api_key"] = value
        else:
            settings_dict["stash"]["api_key"] = None


def _apply_openai_overrides(settings_dict: Dict[str, Any], overrides: Dict[str, Any]):
    """Apply OpenAI-specific overrides with special handling."""
    if "openai" not in overrides:
        return

    if "api_key" in overrides["openai"]:
        settings_dict["openai"]["api_key"] = overrides["openai"]["api_key"]

    if "model" in overrides["openai"]:
        settings_dict["openai"]["model"] = overrides["openai"]["model"]

    if "base_url" in overrides["openai"]:
        # Handle None/null values for base_url
        value = overrides["openai"]["base_url"]
        if value is not None and value != 0:  # Skip 0 values (data error)
            settings_dict["openai"]["base_url"] = value
        else:
            settings_dict["openai"]["base_url"] = None


def _apply_video_ai_overrides(settings_dict: Dict[str, Any], db_settings):
    """Apply video AI settings with special key format handling."""
    video_ai_keys = {
        "analysis_ai_video_server_url": ("analysis", "ai_video_server_url"),
        "analysis_frame_interval": ("analysis", "frame_interval"),
        "analysis_ai_video_threshold": ("analysis", "ai_video_threshold"),
        "analysis_server_timeout": ("analysis", "server_timeout"),
        "analysis_create_markers": ("analysis", "create_markers"),
    }

    for db_key, (section, setting_key) in video_ai_keys.items():
        for setting in db_settings:
            if setting.key == db_key:
                if section not in settings_dict:
                    settings_dict[section] = {}
                settings_dict[section][setting_key] = setting.value
                break


async def load_settings_with_db_overrides() -> Settings:
    """
    Load settings with database overrides for use in background jobs.

    This function is designed to be called from background jobs where
    dependency injection is not available.

    Returns:
        Settings object with database overrides applied
    """
    base_settings = get_settings()

    # Get database overrides
    async with AsyncSessionLocal() as db:
        query = select(Setting)
        result = await db.execute(query)
        db_settings = result.scalars().all()

    # Parse database settings
    overrides = _parse_db_settings(db_settings)

    # Apply overrides to settings
    settings_dict = base_settings.model_dump()

    # Apply section-specific overrides
    _apply_stash_overrides(settings_dict, overrides)
    _apply_openai_overrides(settings_dict, overrides)
    _apply_section_overrides(settings_dict, overrides, "analysis")
    _apply_section_overrides(settings_dict, overrides, "sync")
    _apply_section_overrides(settings_dict, overrides, "qbittorrent")

    # Apply special video AI overrides
    _apply_video_ai_overrides(settings_dict, db_settings)

    # Create new Settings object with overrides
    return Settings(**settings_dict)
