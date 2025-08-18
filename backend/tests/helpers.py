"""Test helper functions."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import Scene, SceneFile


def create_test_scene(
    id: str,
    title: str,
    paths: Optional[List[str]] = None,
    duration: Optional[float] = None,
    **kwargs,
) -> Scene:
    """
    Create a test scene with backward-compatible interface.

    This helper maintains the old API where scenes had paths and duration
    directly, but creates the proper SceneFile relationships.
    """
    # Default values
    if paths is None:
        paths = [f"/{id}.mp4"]

    # Extract file-related fields that might be passed in kwargs
    file_fields = {
        "size": kwargs.pop("size", None),
        "width": kwargs.pop("width", None),
        "height": kwargs.pop("height", None),
        "video_codec": kwargs.pop("video_codec", None),
        "audio_codec": kwargs.pop("audio_codec", None),
        "frame_rate": kwargs.pop("frame_rate", None),
        "bit_rate": kwargs.pop("bit_rate", None),
        "format": kwargs.pop("format", None),
        "oshash": kwargs.pop("oshash", None),
        "phash": kwargs.pop("phash", None),
    }

    # Set default timestamps if not provided
    now = datetime.now()
    kwargs.setdefault("stash_created_at", now)
    kwargs.setdefault("last_synced", now)

    # Set default boolean fields if not provided
    kwargs.setdefault("generated", False)
    kwargs.setdefault("analyzed", False)
    kwargs.setdefault("video_analyzed", False)
    kwargs.setdefault("organized", False)

    # Create the scene
    scene = Scene(id=id, title=title, **kwargs)

    # Create SceneFile objects for each path
    scene.files = []
    for idx, path in enumerate(paths):
        file_kwargs = {
            "id": f"{id}_file_{idx}",
            "scene_id": id,
            "path": path,
            "is_primary": idx == 0,  # First file is primary
            "duration": duration,
            "last_synced": now,
            **{k: v for k, v in file_fields.items() if v is not None},
        }
        scene_file = SceneFile(**file_kwargs)
        scene.files.append(scene_file)

    return scene


def create_scene_with_files(
    scene_data: Dict[str, Any], files_data: Optional[List[Dict[str, Any]]] = None
) -> Scene:
    """
    Create a scene with explicit file data.

    This is for tests that need more control over file properties.
    """
    # Extract scene ID for file creation
    scene_id = scene_data["id"]

    # Set defaults
    now = datetime.now()
    scene_data.setdefault("stash_created_at", now)
    scene_data.setdefault("last_synced", now)

    # Set default boolean fields if not provided
    scene_data.setdefault("generated", False)
    scene_data.setdefault("analyzed", False)
    scene_data.setdefault("video_analyzed", False)
    scene_data.setdefault("organized", False)

    # Create scene
    scene = Scene(**scene_data)

    # Create files if provided
    if files_data:
        scene.files = []
        for idx, file_data in enumerate(files_data):
            file_data.setdefault("id", f"{scene_id}_file_{idx}")
            file_data.setdefault("scene_id", scene_id)
            file_data.setdefault("is_primary", idx == 0)
            file_data.setdefault("last_synced", now)
            scene_file = SceneFile(**file_data)
            scene.files.append(scene_file)

    return scene
