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
        # Convert rating100 (0-100) to rating (0-5)
        rating100 = remote_data.get("rating100")
        if rating100 is not None:
            scene.rating = int(rating100 / 20)  # type: ignore[assignment]
        else:
            scene.rating = remote_data.get("rating")  # type: ignore[assignment]
        scene.organized = remote_data.get("organized", False)

        # Handle file paths
        files = remote_data.get("files", [])
        if files:
            scene.paths = [f.get("path") for f in files if f.get("path")]  # type: ignore[assignment]
        else:
            scene.paths = []  # type: ignore[assignment]

        # Get file properties from the first file
        if files:
            file_data = files[0]
            scene.duration = file_data.get("duration")
            scene.size = file_data.get("size")
            scene.height = file_data.get("height")
            scene.width = file_data.get("width")
            scene.framerate = file_data.get("frame_rate")
            scene.bitrate = file_data.get("bit_rate")
            scene.codec = file_data.get("video_codec")

        # Set Stash timestamps
        created_at_str = remote_data.get("created_at")
        if created_at_str:
            scene.stash_created_at = self._parse_datetime(created_at_str)  # type: ignore[assignment]
        else:
            scene.stash_created_at = datetime.utcnow()  # type: ignore[assignment]

        updated_at_str = remote_data.get("updated_at")
        if updated_at_str:
            scene.stash_updated_at = self._parse_datetime(updated_at_str)  # type: ignore[assignment]

        date_str = remote_data.get("date")
        if date_str:
            scene.stash_date = self._parse_datetime(date_str)  # type: ignore[assignment]
        else:
            scene.stash_date = None  # type: ignore[assignment]

        # Don't overwrite scene.updated_at - let SQLAlchemy handle it
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

        # For Scene entities, compare stash_updated_at instead of updated_at
        if hasattr(local_entity, "stash_updated_at"):
            local_updated = getattr(local_entity, "stash_updated_at", None)
        else:
            # For other entities, use updated_at
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

        # Handle file paths
        files = remote_data.get("files", [])
        if files:
            scene.paths = [f.get("path") for f in files if f.get("path")]  # type: ignore[assignment]
        else:
            scene.paths = []  # type: ignore[assignment]

        # File properties should always be updated from source
        if files:
            file_data = files[0]
            scene.duration = file_data.get("duration")
            scene.size = file_data.get("size")
            scene.height = file_data.get("height")
            scene.width = file_data.get("width")
            scene.framerate = file_data.get("frame_rate")
            scene.bitrate = file_data.get("bit_rate")
            scene.codec = file_data.get("video_codec")

        # Apply tracked changes
        for field, value in changes.items():
            setattr(scene, field, value)

        # Set Stash timestamps
        created_at_str = remote_data.get("created_at")
        if created_at_str:
            scene.stash_created_at = self._parse_datetime(created_at_str)  # type: ignore[assignment]
        else:
            scene.stash_created_at = datetime.utcnow()  # type: ignore[assignment]

        updated_at_str = remote_data.get("updated_at")
        if updated_at_str:
            scene.stash_updated_at = self._parse_datetime(updated_at_str)  # type: ignore[assignment]

        date_str = remote_data.get("date")
        if date_str:
            scene.stash_date = self._parse_datetime(date_str)  # type: ignore[assignment]
        else:
            scene.stash_date = None  # type: ignore[assignment]

        # Update checksum
        scene.content_checksum = self._calculate_checksum(remote_data)  # type: ignore[assignment]
        # Don't overwrite scene.updated_at - let SQLAlchemy handle it

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
