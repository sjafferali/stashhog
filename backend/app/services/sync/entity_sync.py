import logging
from datetime import datetime
from typing import Any, Dict, List, Type, TypeVar

from sqlalchemy.orm import Session

from app.models import Performer, Studio, Tag
from app.services.stash_service import StashService

from .strategies import SyncStrategy

logger = logging.getLogger(__name__)

T = TypeVar("T", Performer, Studio, Tag)


class EntitySyncHandler:
    """Handles synchronization of entities (performers, tags, studios)"""

    def __init__(self, stash_service: StashService, strategy: SyncStrategy):
        self.stash_service = stash_service
        self.strategy = strategy

    async def sync_performers(
        self, stash_performers: List[Dict[str, Any]], db: Session, force: bool = False
    ) -> Dict[str, int]:
        """Sync all performers"""
        logger.info(f"Syncing {len(stash_performers)} performers")

        stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}

        for performer_data in stash_performers:
            try:
                result = await self._sync_single_entity(
                    Performer, performer_data, db, force
                )
                stats["processed"] += 1
                stats[result] += 1

            except Exception as e:
                logger.error(
                    f"Failed to sync performer {performer_data.get('id')}: {str(e)}"
                )
                stats["failed"] += 1

        return stats

    async def sync_tags(
        self, stash_tags: List[Dict[str, Any]], db: Session, force: bool = False
    ) -> Dict[str, int]:
        """Sync all tags"""
        logger.info(f"Syncing {len(stash_tags)} tags")

        stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}

        for tag_data in stash_tags:
            try:
                result = await self._sync_single_entity(Tag, tag_data, db, force)
                stats["processed"] += 1
                stats[result] += 1

            except Exception as e:
                logger.error(f"Failed to sync tag {tag_data.get('id')}: {str(e)}")
                stats["failed"] += 1

        return stats

    async def sync_studios(
        self, stash_studios: List[Dict[str, Any]], db: Session, force: bool = False
    ) -> Dict[str, int]:
        """Sync all studios"""
        logger.info(f"Syncing {len(stash_studios)} studios")

        stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}

        for studio_data in stash_studios:
            try:
                result = await self._sync_single_entity(Studio, studio_data, db, force)
                stats["processed"] += 1
                stats[result] += 1

            except Exception as e:
                logger.error(f"Failed to sync studio {studio_data.get('id')}: {str(e)}")
                stats["failed"] += 1

        return stats

    async def find_or_create_entity(
        self, model_class: Type[T], entity_id: str, name: str, db: Session
    ) -> T:
        """Generic find or create for entities"""
        entity = db.query(model_class).filter(model_class.id == entity_id).first()

        if not entity:
            entity = model_class(id=entity_id, name=name)
            db.add(entity)
            db.flush()

        return entity

    async def _sync_single_entity(
        self,
        model_class: Type[T],
        entity_data: Dict[str, Any],
        db: Session,
        force: bool = False,
    ) -> str:
        """Sync a single entity and return the action taken"""
        entity_id = entity_data.get("id")
        if not entity_id:
            raise ValueError("Entity ID is required")

        # Find existing entity
        existing = db.query(model_class).filter(model_class.id == entity_id).first()

        # Check if we should sync
        if not force and existing:
            should_sync = await self.strategy.should_sync(entity_data, existing)
            if not should_sync:
                return "skipped"

        # Create or update entity
        if not existing:
            entity = model_class(id=entity_id)
            db.add(entity)
            action = "created"
        else:
            entity = existing
            action = "updated"

        # Apply entity-specific updates
        if isinstance(entity, Performer):
            self._update_performer(entity, entity_data)
        elif isinstance(entity, Tag):
            self._update_tag(entity, entity_data)
        elif isinstance(entity, Studio):
            self._update_studio(entity, entity_data)

        # Common updates
        entity.last_synced = datetime.utcnow()  # type: ignore[assignment]

        db.flush()
        return action

    def _update_performer(self, performer: Performer, data: Dict[str, Any]) -> None:
        """Update performer-specific fields"""
        performer.name = data.get("name", "")
        performer.aliases = data.get("aliases")  # type: ignore[assignment]
        performer.gender = data.get("gender")  # type: ignore[assignment]
        performer.birthdate = data.get("birthdate")  # type: ignore[assignment]
        performer.country = data.get("country")  # type: ignore[assignment]
        performer.ethnicity = data.get("ethnicity")  # type: ignore[assignment]
        performer.hair_color = data.get("hair_color")  # type: ignore[assignment]
        performer.eye_color = data.get("eye_color")  # type: ignore[assignment]
        performer.height_cm = data.get("height")  # type: ignore[assignment]
        performer.weight_kg = data.get("weight")  # type: ignore[assignment]
        performer.measurements = data.get("measurements")  # type: ignore[assignment]
        performer.fake_tits = data.get("fake_tits")  # type: ignore[assignment]
        performer.career_length = data.get("career_length")  # type: ignore[assignment]
        performer.tattoos = data.get("tattoos")  # type: ignore[assignment]
        performer.piercings = data.get("piercings")  # type: ignore[assignment]
        performer.url = data.get("url")  # type: ignore[assignment]
        performer.twitter = data.get("twitter")  # type: ignore[assignment]
        performer.instagram = data.get("instagram")  # type: ignore[assignment]
        performer.details = data.get("details")  # type: ignore[assignment]
        performer.rating = data.get("rating")  # type: ignore[assignment]
        performer.favorite = data.get("favorite", False)
        performer.ignore_auto_tag = data.get("ignore_auto_tag", False)
        performer.updated_at = datetime.utcnow()  # type: ignore[assignment]

        # Handle image URL
        if data.get("image_path"):
            performer.image_url = data["image_path"]

    def _update_tag(self, tag: Tag, data: Dict[str, Any]) -> None:
        """Update tag-specific fields"""
        tag.name = data.get("name", "")
        tag.aliases = data.get("aliases")  # type: ignore[assignment]
        tag.description = data.get("description")  # type: ignore[assignment]
        tag.ignore_auto_tag = data.get("ignore_auto_tag", False)
        tag.updated_at = datetime.utcnow()  # type: ignore[assignment]

        # Handle parent tag
        if data.get("parent") and data["parent"].get("id"):
            # We'll need to ensure the parent exists
            # This is handled in a separate pass to avoid circular dependencies
            tag.parent_temp_id = data["parent"]["id"]

    def _update_studio(self, studio: Studio, data: Dict[str, Any]) -> None:
        """Update studio-specific fields"""
        studio.name = data.get("name", "")
        studio.aliases = data.get("aliases")  # type: ignore[assignment]
        studio.url = data.get("url")  # type: ignore[assignment]
        studio.details = data.get("details")  # type: ignore[assignment]
        studio.rating = data.get("rating")  # type: ignore[assignment]
        studio.favorite = data.get("favorite", False)
        studio.ignore_auto_tag = data.get("ignore_auto_tag", False)
        studio.updated_at = datetime.utcnow()  # type: ignore[assignment]

        # Handle parent studio
        if data.get("parent") and data["parent"].get("id"):
            studio.parent_temp_id = data["parent"]["id"]

        # Handle image URL
        if data.get("image_path"):
            studio.image_url = data["image_path"]

    async def resolve_tag_hierarchy(self, db: Session) -> None:
        """Resolve parent-child relationships for tags after all are synced"""
        tags_with_parents = db.query(Tag).filter(Tag.parent_temp_id.isnot(None)).all()

        for tag in tags_with_parents:
            parent = db.query(Tag).filter(Tag.id == tag.parent_temp_id).first()
            if parent:
                tag.parent_id = parent.id
            else:
                logger.warning(
                    f"Parent tag {tag.parent_temp_id} not found for tag {tag.id}"
                )
                tag.parent_temp_id = None  # type: ignore[assignment]

    async def resolve_studio_hierarchy(self, db: Session) -> None:
        """Resolve parent-child relationships for studios after all are synced"""
        studios_with_parents = (
            db.query(Studio).filter(Studio.parent_temp_id.isnot(None)).all()
        )

        for studio in studios_with_parents:
            parent = db.query(Studio).filter(Studio.id == studio.parent_temp_id).first()
            if parent:
                studio.parent_id = parent.id
            else:
                logger.warning(
                    f"Parent studio {studio.parent_temp_id} not found for studio {studio.id}"
                )
                studio.parent_temp_id = None  # type: ignore[assignment]
