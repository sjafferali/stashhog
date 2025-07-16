import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.models import Performer, Scene, Studio, Tag

logger = logging.getLogger(__name__)


class ConflictStrategy(str, Enum):
    REMOTE_WINS = "remote_wins"
    LOCAL_WINS = "local_wins"
    MERGE = "merge"
    MANUAL = "manual"


class ConflictType(str, Enum):
    FIELD_MISMATCH = "field_mismatch"
    RELATIONSHIP_MISMATCH = "relationship_mismatch"
    DELETION_CONFLICT = "deletion_conflict"
    VERSION_CONFLICT = "version_conflict"


class ConflictResolver:
    """Handles conflicts between local and remote data during sync"""

    def __init__(
        self, default_strategy: ConflictStrategy = ConflictStrategy.REMOTE_WINS
    ):
        self.default_strategy = default_strategy
        self.conflict_log: List[Dict[str, Any]] = []

    def resolve_scene_conflict(
        self,
        local: Scene,
        remote: Dict[str, Any],
        strategy: Optional[ConflictStrategy] = None,
    ) -> Scene:
        """Resolve conflicts between local and remote scene data"""
        strategy = strategy or self.default_strategy

        # Detect changes
        changes = self.detect_changes(local, remote)

        if not changes:
            return local

        # Log conflict
        self._log_conflict(
            entity_type="scene",
            entity_id=str(local.id),
            changes=changes,
            strategy=strategy,
        )

        # Apply resolution strategy
        if strategy == ConflictStrategy.REMOTE_WINS:
            return self._apply_remote_wins(local, remote)  # type: ignore[no-any-return]
        elif strategy == ConflictStrategy.LOCAL_WINS:
            return local  # No changes needed
        elif strategy == ConflictStrategy.MERGE:
            return self._apply_merge_strategy(local, remote, changes)  # type: ignore[no-any-return]
        elif strategy == ConflictStrategy.MANUAL:
            # In manual mode, we skip the update and flag for review
            local.sync_conflict = True
            local.conflict_data = changes
            return local

        return local

    def detect_changes(self, local: Any, remote: Dict[str, Any]) -> Dict[str, Any]:
        """Detect what fields have changed between local and remote"""
        changes = {}

        if isinstance(local, Scene):
            changes.update(self._detect_scene_changes(local, remote))
        elif isinstance(local, Performer):
            changes.update(self._detect_performer_changes(local, remote))
        elif isinstance(local, Tag):
            changes.update(self._detect_tag_changes(local, remote))
        elif isinstance(local, Studio):
            changes.update(self._detect_studio_changes(local, remote))

        return changes

    def _detect_scene_changes(
        self, local: Scene, remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect changes in scene fields"""
        changes = {}

        # Check basic fields
        field_map = {
            "title": "title",
            "details": "details",
            "url": "url",
            "date": "date",
            "rating": "rating",
            "organized": "organized",
        }

        for local_field, remote_field in field_map.items():
            local_value = getattr(local, local_field, None)
            remote_value = remote.get(remote_field)

            if local_value != remote_value:
                changes[local_field] = {
                    "local": local_value,
                    "remote": remote_value,
                    "type": ConflictType.FIELD_MISMATCH,
                }

        # Check file properties
        file_data = remote.get("file", {})
        file_fields = {
            "duration": "duration",
            "size": "size",
            "height": "height",
            "width": "width",
            "framerate": "framerate",
            "bitrate": "bitrate",
            "codec": "video_codec",
        }

        for local_field, remote_field in file_fields.items():
            local_value = getattr(local, local_field, None)
            remote_value = file_data.get(remote_field)

            if local_value != remote_value:
                changes[f"file.{local_field}"] = {
                    "local": local_value,
                    "remote": remote_value,
                    "type": ConflictType.FIELD_MISMATCH,
                }

        # Check relationships
        changes.update(self._detect_relationship_changes(local, remote))

        return changes

    def _detect_performer_changes(
        self, local: Performer, remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect changes in performer fields"""
        changes = {}

        field_map = {
            "name": "name",
            "aliases": "aliases",
            "gender": "gender",
            "birthdate": "birthdate",
            "url": "url",
            "rating": "rating",
        }

        for local_field, remote_field in field_map.items():
            local_value = getattr(local, local_field, None)
            remote_value = remote.get(remote_field)

            if local_value != remote_value:
                changes[local_field] = {
                    "local": local_value,
                    "remote": remote_value,
                    "type": ConflictType.FIELD_MISMATCH,
                }

        return changes

    def _detect_tag_changes(self, local: Tag, remote: Dict[str, Any]) -> Dict[str, Any]:
        """Detect changes in tag fields"""
        changes = {}

        if local.name != remote.get("name"):
            changes["name"] = {
                "local": local.name,
                "remote": remote.get("name"),
                "type": ConflictType.FIELD_MISMATCH,
            }

        return changes

    def _detect_studio_changes(
        self, local: Studio, remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect changes in studio fields"""
        changes = {}

        field_map = {
            "name": "name",
            "url": "url",
            "details": "details",
            "rating": "rating",
        }

        for local_field, remote_field in field_map.items():
            local_value = getattr(local, local_field, None)
            remote_value = remote.get(remote_field)

            if local_value != remote_value:
                changes[local_field] = {
                    "local": local_value,
                    "remote": remote_value,
                    "type": ConflictType.FIELD_MISMATCH,
                }

        return changes

    def _detect_relationship_changes(
        self, local: Scene, remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect changes in scene relationships"""
        changes = {}

        # Check performers
        local_performer_ids = {p.id for p in local.performers}
        remote_performer_ids = {p["id"] for p in remote.get("performers", [])}

        if local_performer_ids != remote_performer_ids:
            changes["performers"] = {
                "local": list(local_performer_ids),
                "remote": list(remote_performer_ids),
                "added": list(remote_performer_ids - local_performer_ids),
                "removed": list(local_performer_ids - remote_performer_ids),
                "type": ConflictType.RELATIONSHIP_MISMATCH,
            }

        # Check tags
        local_tag_ids = {t.id for t in local.tags}
        remote_tag_ids = {t["id"] for t in remote.get("tags", [])}

        if local_tag_ids != remote_tag_ids:
            changes["tags"] = {
                "local": list(local_tag_ids),
                "remote": list(remote_tag_ids),
                "added": list(remote_tag_ids - local_tag_ids),
                "removed": list(local_tag_ids - remote_tag_ids),
                "type": ConflictType.RELATIONSHIP_MISMATCH,
            }

        # Check studio
        local_studio_id = local.studio.id if local.studio else None
        remote_studio_id = remote.get("studio", {}).get("id")

        if local_studio_id != remote_studio_id:
            changes["studio"] = {
                "local": local_studio_id,
                "remote": remote_studio_id,
                "type": ConflictType.RELATIONSHIP_MISMATCH,
            }

        return changes

    def _apply_remote_wins(self, local: Any, remote: Dict[str, Any]) -> Any:
        """Apply remote data, overwriting local changes"""
        if isinstance(local, Scene):
            local.title = remote.get("title", "")
            local.details = remote.get("details")  # type: ignore[assignment]
            local.url = remote.get("url")  # type: ignore[assignment]
            local.date = remote.get("date")  # type: ignore[assignment]
            local.rating = remote.get("rating")  # type: ignore[assignment]
            local.organized = remote.get("organized", False)

            file_data = remote.get("file", {})
            local.duration = file_data.get("duration")
            local.size = file_data.get("size")
            local.height = file_data.get("height")
            local.width = file_data.get("width")
            local.framerate = file_data.get("framerate")
            local.bitrate = file_data.get("bitrate")
            local.codec = file_data.get("video_codec")

        return local

    def _apply_merge_strategy(
        self, local: Any, remote: Dict[str, Any], changes: Dict[str, Any]
    ) -> Any:
        """Apply intelligent merge strategy"""
        if isinstance(local, Scene):
            # For scenes, we can be more selective about what to merge

            # Always take file properties from remote (source of truth)
            file_data = remote.get("file", {})
            local.duration = file_data.get("duration")
            local.size = file_data.get("size")
            local.height = file_data.get("height")
            local.width = file_data.get("width")
            local.framerate = file_data.get("framerate")
            local.bitrate = file_data.get("bitrate")
            local.codec = file_data.get("video_codec")

            # For other fields, check if local has been manually edited
            # (This would require tracking manual edits in the database)
            if not getattr(local, "manually_edited", False):
                local.title = remote.get("title", local.title)
                local.details = remote.get("details", local.details)
                local.url = remote.get("url", local.url)
                local.date = remote.get("date", local.date)

            # Merge relationships additively
            # This is handled in the sync handler

        return local

    def _log_conflict(
        self,
        entity_type: str,
        entity_id: str,
        changes: Dict[str, Any],
        strategy: ConflictStrategy,
    ) -> None:
        """Log conflict for auditing"""
        conflict_entry = {
            "timestamp": datetime.utcnow(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "changes": changes,
            "strategy": strategy.value,
            "resolved": True,
        }

        self.conflict_log.append(conflict_entry)

        logger.info(
            f"Conflict resolved for {entity_type} {entity_id} "
            f"using {strategy.value} strategy. "
            f"{len(changes)} fields affected."
        )

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of conflicts encountered"""
        return {
            "total_conflicts": len(self.conflict_log),
            "by_type": self._count_by_field(self.conflict_log, "entity_type"),
            "by_strategy": self._count_by_field(self.conflict_log, "strategy"),
            "recent_conflicts": self.conflict_log[-10:],  # Last 10 conflicts
        }

    def _count_by_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        """Count occurrences by field value"""
        counts: Dict[str, int] = {}
        for item in items:
            value = item.get(field)
            if value is not None:
                counts[str(value)] = counts.get(str(value), 0) + 1
        return counts
