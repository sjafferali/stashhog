"""Data transformation utilities for Stash API."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _extract_paths_list(paths_data: Optional[Any]) -> List[str]:
    """Extract paths list from either dict or list format."""
    if not paths_data:
        return []

    # Handle paths as a dictionary (new format from Stash API)
    if isinstance(paths_data, dict):
        # Return URLs from the dictionary as a list
        return [url for url in paths_data.values() if url]

    # Handle paths as a list (legacy format)
    elif isinstance(paths_data, list):
        return [p.get("path", "") for p in paths_data if isinstance(p, dict)]

    return []


def transform_scene(stash_scene: Dict) -> Dict:
    """Convert Stash scene to internal format."""
    if not stash_scene:
        logger.debug("transform_scene called with empty/None stash_scene")
        return {}

    scene_id = stash_scene.get("id", "unknown")
    logger.debug(f"transform_scene called for scene {scene_id}")

    # Extract actual file path from files array
    file_path = None
    primary_path = ""
    files = stash_scene.get("files", [])
    if files and len(files) > 0:
        file_path = files[0].get("path")
        # Use actual file path as primary path
        primary_path = file_path or ""

    # Transform to internal format
    logger.debug(f"Transforming scene {scene_id} to internal format")
    try:
        transformed = {
            "id": stash_scene.get("id"),
            "title": stash_scene.get("title", ""),
            "path": primary_path,
            "paths": _extract_paths_list(stash_scene.get("paths")),
            "file_path": file_path,  # Add actual file path
            "details": stash_scene.get("details"),
            "date": stash_scene.get("date"),
            "rating": stash_scene.get("rating100"),
            "organized": stash_scene.get("organized", False),
            "o_counter": stash_scene.get("o_counter", 0),
            "created_at": stash_scene.get("created_at"),
            "updated_at": stash_scene.get("updated_at"),
            "studio": (
                transform_studio(stash_scene.get("studio", {}))
                if stash_scene.get("studio") is not None
                else None
            ),
            "performers": [
                transform_performer(p) for p in stash_scene.get("performers", [])
            ],
            "tags": [transform_tag(t) for t in stash_scene.get("tags", [])],
            "file": transform_file_info(
                stash_scene.get("files", [{}])[0] if stash_scene.get("files") else None
            ),
            "galleries": stash_scene.get("galleries", []),
            "movies": stash_scene.get("movies", []),
        }
        logger.debug(f"Scene {scene_id} transformed successfully")
        return transformed
    except Exception as e:
        logger.error(f"Error transforming scene {scene_id}: {str(e)}")
        logger.debug(f"Transform exception type: {type(e).__name__}, value: {repr(e)}")
        logger.debug(
            f"Scene data keys: {list(stash_scene.keys()) if stash_scene else 'None'}"
        )
        raise


def transform_performer(stash_performer: Dict) -> Dict:
    """Convert Stash performer to internal format."""
    if not stash_performer:
        logger.debug("transform_performer returning empty dict for falsy input")
        return {}

    # Debug logging
    if not stash_performer.get("id"):
        logger.error(f"Performer missing 'id' field: {stash_performer}")

    return {
        "id": stash_performer.get("id"),  # Primary key from Stash
        "name": stash_performer.get("name", ""),
        "gender": stash_performer.get("gender"),
        "url": stash_performer.get("url"),
        "birthdate": stash_performer.get("birthdate"),
        "ethnicity": stash_performer.get("ethnicity"),
        "country": stash_performer.get("country"),
        "eye_color": stash_performer.get("eye_color"),
        "height_cm": stash_performer.get("height_cm"),
        "measurements": stash_performer.get("measurements"),
        "fake_tits": stash_performer.get("fake_tits"),
        "career_length": stash_performer.get("career_length"),
        "tattoos": stash_performer.get("tattoos"),
        "piercings": stash_performer.get("piercings"),
        "aliases": stash_performer.get("alias_list", []),
        "favorite": stash_performer.get("favorite", False),
        "rating": stash_performer.get("rating100"),
        "details": stash_performer.get("details"),
        "death_date": stash_performer.get("death_date"),
        "hair_color": stash_performer.get("hair_color"),
        "weight": stash_performer.get("weight"),
        "twitter": stash_performer.get("twitter"),
        "instagram": stash_performer.get("instagram"),
        "ignore_auto_tag": stash_performer.get("ignore_auto_tag", False),
    }


def transform_tag(stash_tag: Dict) -> Dict:
    """Convert Stash tag to internal format."""
    if not stash_tag:
        logger.debug("transform_tag returning empty dict for falsy input")
        return {}

    # Debug logging
    if not stash_tag.get("id"):
        logger.error(f"Tag missing 'id' field: {stash_tag}")

    return {
        "id": stash_tag.get("id"),  # Primary key from Stash
        "name": stash_tag.get("name", ""),
        "description": stash_tag.get("description"),
        "aliases": stash_tag.get("aliases", []),
        "scene_count": stash_tag.get("scene_count", 0),
        "performer_count": stash_tag.get("performer_count", 0),
        "studio_count": stash_tag.get("studio_count", 0),
        "movie_count": stash_tag.get("movie_count", 0),
        "gallery_count": stash_tag.get("gallery_count", 0),
        "image_count": stash_tag.get("image_count", 0),
        "ignore_auto_tag": stash_tag.get("ignore_auto_tag", False),
    }


def transform_studio(stash_studio: Dict[Any, Any]) -> Dict:
    """Convert Stash studio to internal format."""
    logger.debug(
        f"transform_studio called with type: {type(stash_studio)}, value: {stash_studio}"
    )
    if not stash_studio:
        logger.debug("transform_studio returning empty dict for falsy input")
        return {}

    # Debug logging
    studio_id = stash_studio.get("id")
    if not studio_id:
        logger.error(f"Studio missing 'id' field: {stash_studio}")
    else:
        logger.debug(f"Transforming studio {studio_id}")

    try:
        result = {
            "id": stash_studio.get("id"),  # Primary key from Stash
            "name": stash_studio.get("name", ""),
            "url": stash_studio.get("url"),
            "details": stash_studio.get("details"),
            "rating": stash_studio.get("rating100"),
            "scene_count": stash_studio.get("scene_count", 0),
            "aliases": stash_studio.get("aliases", []),
            "ignore_auto_tag": stash_studio.get("ignore_auto_tag", False),
        }
        logger.debug(f"Studio {studio_id} transformed successfully")
        return result
    except Exception as e:
        logger.error(f"Error transforming studio: {str(e)}")
        logger.debug(
            f"Studio transform exception type: {type(e).__name__}, value: {repr(e)}"
        )
        raise


def transform_file_info(file_info: Optional[Dict]) -> Dict:
    """Transform file information."""
    if not file_info:
        logger.debug("transform_file_info returning empty dict for falsy input")
        return {}

    logger.debug(
        f"Transforming file info with keys: {list(file_info.keys()) if file_info else 'None'}"
    )

    return {
        "size": file_info.get("size", 0),
        "duration": file_info.get("duration", 0),
        "video_codec": file_info.get("video_codec"),
        "audio_codec": file_info.get("audio_codec"),
        "width": file_info.get("width", 0),
        "height": file_info.get("height", 0),
        "framerate": file_info.get("frame_rate", 0),
        "bitrate": file_info.get("bit_rate", 0),
    }


def prepare_scene_update(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare updates for Stash mutation."""
    # Map internal field names to Stash field names
    field_mapping = {
        "id": "id",
        "rating": "rating100",
        "o_counter": "o_counter",
        "studio_id": "studio_id",
        "performer_ids": "performer_ids",
        "tag_ids": "tag_ids",
        "movie_ids": "movie_ids",
        "gallery_ids": "gallery_ids",
    }

    stash_updates: Dict[str, Any] = {}

    for key, value in updates.items():
        # Skip None values
        if value is None:
            continue

        # Map field names
        stash_key = field_mapping.get(key, key)

        # Handle special cases
        if key == "performers" and isinstance(value, list):
            # Convert performer objects to IDs
            stash_updates["performer_ids"] = [
                p.get("id") if isinstance(p, dict) else p for p in value
            ]
        elif key == "tags" and isinstance(value, list):
            # Convert tag objects to IDs
            stash_updates["tag_ids"] = [
                t.get("id") if isinstance(t, dict) else t for t in value
            ]
        elif key == "studio" and isinstance(value, dict):
            # Convert studio object to ID
            stash_updates["studio_id"] = value.get("id") if value else None
        elif key == "studio_id":
            stash_updates["studio_id"] = value
        else:
            stash_updates[stash_key] = value

    return stash_updates


def prepare_bulk_scene_updates(updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare multiple scene updates for bulk mutation."""
    return [prepare_scene_update(update) for update in updates]
