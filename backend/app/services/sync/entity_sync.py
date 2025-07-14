import logging
from typing import Dict, Any, List, Optional, Type, TypeVar
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Performer, Tag, Studio
from app.services.stash_service import StashService
from .strategies import SyncStrategy

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EntitySyncHandler:
    """Handles synchronization of entities (performers, tags, studios)"""
    
    def __init__(self, stash_service: StashService, strategy: SyncStrategy):
        self.stash_service = stash_service
        self.strategy = strategy
    
    async def sync_performers(
        self,
        stash_performers: List[Dict[str, Any]],
        db: Session,
        force: bool = False
    ) -> Dict[str, int]:
        """Sync all performers"""
        logger.info(f"Syncing {len(stash_performers)} performers")
        
        stats = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for performer_data in stash_performers:
            try:
                result = await self._sync_single_entity(
                    Performer,
                    performer_data,
                    db,
                    force
                )
                stats["processed"] += 1
                stats[result] += 1
                
            except Exception as e:
                logger.error(f"Failed to sync performer {performer_data.get('id')}: {str(e)}")
                stats["failed"] += 1
        
        return stats
    
    async def sync_tags(
        self,
        stash_tags: List[Dict[str, Any]],
        db: Session,
        force: bool = False
    ) -> Dict[str, int]:
        """Sync all tags"""
        logger.info(f"Syncing {len(stash_tags)} tags")
        
        stats = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for tag_data in stash_tags:
            try:
                result = await self._sync_single_entity(
                    Tag,
                    tag_data,
                    db,
                    force
                )
                stats["processed"] += 1
                stats[result] += 1
                
            except Exception as e:
                logger.error(f"Failed to sync tag {tag_data.get('id')}: {str(e)}")
                stats["failed"] += 1
        
        return stats
    
    async def sync_studios(
        self,
        stash_studios: List[Dict[str, Any]],
        db: Session,
        force: bool = False
    ) -> Dict[str, int]:
        """Sync all studios"""
        logger.info(f"Syncing {len(stash_studios)} studios")
        
        stats = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for studio_data in stash_studios:
            try:
                result = await self._sync_single_entity(
                    Studio,
                    studio_data,
                    db,
                    force
                )
                stats["processed"] += 1
                stats[result] += 1
                
            except Exception as e:
                logger.error(f"Failed to sync studio {studio_data.get('id')}: {str(e)}")
                stats["failed"] += 1
        
        return stats
    
    async def find_or_create_entity(
        self,
        model_class: Type[T],
        stash_id: str,
        name: str,
        db: Session
    ) -> T:
        """Generic find or create for entities"""
        entity = db.query(model_class).filter(model_class.stash_id == stash_id).first()
        
        if not entity:
            entity = model_class(stash_id=stash_id, name=name)
            db.add(entity)
            db.flush()
        
        return entity
    
    async def _sync_single_entity(
        self,
        model_class: Type[T],
        entity_data: Dict[str, Any],
        db: Session,
        force: bool = False
    ) -> str:
        """Sync a single entity and return the action taken"""
        entity_id = entity_data.get("id")
        if not entity_id:
            raise ValueError("Entity ID is required")
        
        # Find existing entity
        existing = db.query(model_class).filter(model_class.stash_id == entity_id).first()
        
        # Check if we should sync
        if not force and existing:
            should_sync = await self.strategy.should_sync(entity_data, existing)
            if not should_sync:
                return "skipped"
        
        # Create or update entity
        if not existing:
            entity = model_class(stash_id=entity_id)
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
        entity.last_synced = datetime.utcnow()
        
        db.flush()
        return action
    
    def _update_performer(self, performer: Performer, data: Dict[str, Any]):
        """Update performer-specific fields"""
        performer.name = data.get("name", "")
        performer.aliases = data.get("aliases")
        performer.gender = data.get("gender")
        performer.birthdate = data.get("birthdate")
        performer.country = data.get("country")
        performer.ethnicity = data.get("ethnicity")
        performer.hair_color = data.get("hair_color")
        performer.eye_color = data.get("eye_color")
        performer.height_cm = data.get("height")
        performer.weight_kg = data.get("weight")
        performer.measurements = data.get("measurements")
        performer.fake_tits = data.get("fake_tits")
        performer.career_length = data.get("career_length")
        performer.tattoos = data.get("tattoos")
        performer.piercings = data.get("piercings")
        performer.url = data.get("url")
        performer.twitter = data.get("twitter")
        performer.instagram = data.get("instagram")
        performer.details = data.get("details")
        performer.rating = data.get("rating")
        performer.favorite = data.get("favorite", False)
        performer.ignore_auto_tag = data.get("ignore_auto_tag", False)
        performer.updated_at = datetime.utcnow()
        
        # Handle image URL
        if data.get("image_path"):
            performer.image_url = data["image_path"]
    
    def _update_tag(self, tag: Tag, data: Dict[str, Any]):
        """Update tag-specific fields"""
        tag.name = data.get("name", "")
        tag.aliases = data.get("aliases")
        tag.description = data.get("description")
        tag.ignore_auto_tag = data.get("ignore_auto_tag", False)
        tag.updated_at = datetime.utcnow()
        
        # Handle parent tag
        if data.get("parent") and data["parent"].get("id"):
            # We'll need to ensure the parent exists
            # This is handled in a separate pass to avoid circular dependencies
            tag.parent_stash_id = data["parent"]["id"]
    
    def _update_studio(self, studio: Studio, data: Dict[str, Any]):
        """Update studio-specific fields"""
        studio.name = data.get("name", "")
        studio.aliases = data.get("aliases")
        studio.url = data.get("url")
        studio.details = data.get("details")
        studio.rating = data.get("rating")
        studio.favorite = data.get("favorite", False)
        studio.ignore_auto_tag = data.get("ignore_auto_tag", False)
        studio.updated_at = datetime.utcnow()
        
        # Handle parent studio
        if data.get("parent") and data["parent"].get("id"):
            studio.parent_stash_id = data["parent"]["id"]
        
        # Handle image URL
        if data.get("image_path"):
            studio.image_url = data["image_path"]
    
    async def resolve_tag_hierarchy(self, db: Session):
        """Resolve parent-child relationships for tags after all are synced"""
        tags_with_parents = db.query(Tag).filter(Tag.parent_stash_id.isnot(None)).all()
        
        for tag in tags_with_parents:
            parent = db.query(Tag).filter(Tag.stash_id == tag.parent_stash_id).first()
            if parent:
                tag.parent_id = parent.id
            else:
                logger.warning(f"Parent tag {tag.parent_stash_id} not found for tag {tag.id}")
                tag.parent_stash_id = None
    
    async def resolve_studio_hierarchy(self, db: Session):
        """Resolve parent-child relationships for studios after all are synced"""
        studios_with_parents = db.query(Studio).filter(Studio.parent_stash_id.isnot(None)).all()
        
        for studio in studios_with_parents:
            parent = db.query(Studio).filter(Studio.stash_id == studio.parent_stash_id).first()
            if parent:
                studio.parent_id = parent.id
            else:
                logger.warning(f"Parent studio {studio.parent_stash_id} not found for studio {studio.id}")
                studio.parent_stash_id = None