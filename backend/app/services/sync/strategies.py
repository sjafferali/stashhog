import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Union

from app.models import Performer, Scene, Studio, Tag


class SyncStrategy(ABC):
    """Base class for sync strategies"""

    @abstractmethod
    async def should_sync(
        self, remote_data: Dict[str, Any], local_entity: Optional[Any]
    ) -> bool:
        """Determine if an entity should be synced"""
        pass

    @abstractmethod
    async def merge_data(self, local_entity: Any, remote_data: Dict[str, Any]) -> Any:
        """Merge remote data into local entity"""
        pass


class FullSyncStrategy(SyncStrategy):
    """Always sync everything - useful for initial imports or forced refreshes"""

    async def should_sync(
        self, remote_data: Dict[str, Any], local_entity: Optional[Any]
    ) -> bool:
        return True

    async def merge_data(self, local_entity: Any, remote_data: Dict[str, Any]) -> Any:
        # Always overwrite with remote data
        return self._apply_remote_data(local_entity, remote_data)

    def _apply_remote_data(self, local_entity: Any, remote_data: Dict[str, Any]) -> Any:
        """Apply all remote data to local entity"""
        if isinstance(local_entity, Scene):
            return self._merge_scene_data(local_entity, remote_data)
        elif isinstance(local_entity, (Performer, Tag, Studio)):
            return self._merge_entity_data(local_entity, remote_data)
        return local_entity

    def _merge_scene_data(self, scene: Scene, remote_data: Dict[str, Any]) -> Scene:
        scene.title = remote_data.get("title", "")
        scene.details = remote_data.get("details")  # type: ignore[assignment]
        scene.url = remote_data.get("url")  # type: ignore[assignment]
        scene.date = remote_data.get("date")  # type: ignore[assignment]
        scene.rating = remote_data.get("rating")  # type: ignore[assignment]
        scene.organized = remote_data.get("organized", False)
        scene.duration = remote_data.get("file", {}).get("duration")
        scene.size = remote_data.get("file", {}).get("size")
        scene.height = remote_data.get("file", {}).get("height")
        scene.width = remote_data.get("file", {}).get("width")
        scene.framerate = remote_data.get("file", {}).get("framerate")
        scene.bitrate = remote_data.get("file", {}).get("bitrate")
        scene.codec = remote_data.get("file", {}).get("video_codec")
        scene.updated_at = datetime.utcnow()  # type: ignore[assignment]
        return scene

    def _merge_entity_data(
        self, entity: Union[Performer, Tag, Studio], remote_data: Dict[str, Any]
    ) -> Union[Performer, Tag, Studio]:
        entity.name = remote_data.get("name", "")
        if hasattr(entity, "aliases"):
            entity.aliases = remote_data.get("aliases")  # type: ignore[assignment]
        if hasattr(entity, "url"):
            entity.url = remote_data.get("url")
        if hasattr(entity, "rating"):
            entity.rating = remote_data.get("rating")
        entity.updated_at = datetime.utcnow()  # type: ignore[assignment]
        return entity


class IncrementalSyncStrategy(SyncStrategy):
    """Only sync if remote is newer than local based on updated_at timestamp"""

    async def should_sync(
        self, remote_data: Dict[str, Any], local_entity: Optional[Any]
    ) -> bool:
        if not local_entity:
            return True

        # Parse remote updated_at
        remote_updated = self._parse_datetime(remote_data.get("updated_at"))
        if not remote_updated:
            return True

        # Compare with local updated_at
        local_updated = getattr(local_entity, "updated_at", None)
        if not local_updated:
            return True

        return bool(remote_updated > local_updated)

    async def merge_data(self, local_entity: Any, remote_data: Dict[str, Any]) -> Any:
        strategy = FullSyncStrategy()
        return strategy._apply_remote_data(local_entity, remote_data)

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            # Handle ISO format with timezone
            if "T" in dt_str:
                if "+" in dt_str or dt_str.endswith("Z"):
                    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                return datetime.fromisoformat(dt_str)
            return datetime.strptime(dt_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None


class SmartSyncStrategy(SyncStrategy):
    """Intelligent sync based on checksums and change detection"""

    async def should_sync(
        self, remote_data: Dict[str, Any], local_entity: Optional[Any]
    ) -> bool:
        if not local_entity:
            return True

        # First try incremental check
        incremental = IncrementalSyncStrategy()
        if await incremental.should_sync(remote_data, local_entity):
            return True

        # Then check if content has actually changed
        remote_checksum = self._calculate_checksum(remote_data)
        local_checksum = getattr(local_entity, "content_checksum", None)

        if not local_checksum or remote_checksum != local_checksum:
            return True

        return False

    async def merge_data(self, local_entity: Any, remote_data: Dict[str, Any]) -> Any:
        # Apply changes intelligently
        if isinstance(local_entity, Scene):
            return await self._smart_merge_scene(local_entity, remote_data)
        else:
            # For other entities, use full sync
            strategy = FullSyncStrategy()
            return strategy._apply_remote_data(local_entity, remote_data)

    async def _smart_merge_scene(
        self, scene: Scene, remote_data: Dict[str, Any]
    ) -> Scene:
        """Intelligently merge scene data, preserving local changes where appropriate"""
        changes = {}

        # Track what fields have changed
        if scene.title != remote_data.get("title", ""):
            changes["title"] = remote_data.get("title", "")

        if scene.details != remote_data.get("details"):
            changes["details"] = remote_data.get("details")

        if scene.url != remote_data.get("url"):
            changes["url"] = remote_data.get("url")

        if scene.date != remote_data.get("date"):
            changes["date"] = remote_data.get("date")

        # File properties should always be updated from source
        file_data = remote_data.get("file", {})
        scene.duration = file_data.get("duration")
        scene.size = file_data.get("size")
        scene.height = file_data.get("height")
        scene.width = file_data.get("width")
        scene.framerate = file_data.get("framerate")
        scene.bitrate = file_data.get("bitrate")
        scene.codec = file_data.get("video_codec")

        # Apply tracked changes
        for field, value in changes.items():
            setattr(scene, field, value)

        # Update checksum
        scene.content_checksum = self._calculate_checksum(remote_data)  # type: ignore[assignment]
        scene.updated_at = datetime.utcnow()  # type: ignore[assignment]

        return scene

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate a checksum for the important fields of an entity"""
        # Select fields that matter for comparison
        important_fields = {
            "title",
            "details",
            "url",
            "date",
            "rating",
            "organized",
            "file",
            "performers",
            "tags",
            "studio",
        }

        checksum_data = {
            k: v for k, v in data.items() if k in important_fields and v is not None
        }

        # Convert to stable JSON string
        json_str = json.dumps(checksum_data, sort_keys=True, default=str)

        # Calculate SHA256 hash
        return hashlib.sha256(json_str.encode()).hexdigest()
