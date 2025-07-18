import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Performer, Scene, Studio, SyncHistory, Tag
from app.models.base import BaseModel

logger = logging.getLogger(__name__)


class SyncRepository:
    """Repository for sync-related database operations"""

    def bulk_upsert_scenes(
        self, scenes: List[Dict[str, Any]], db: Session
    ) -> List[Scene]:
        """Efficiently upsert multiple scenes using bulk operations"""
        if not scenes:
            return []

        # Prepare data for bulk insert
        scene_data = []
        for scene in scenes:
            scene_dict = {
                "id": scene["id"],
                "title": scene.get("title", ""),
                "details": scene.get("details"),
                "url": scene.get("url"),
                "rating": scene.get("rating"),
                "organized": scene.get("organized", False),
                "duration": scene.get("file", {}).get("duration"),
                "size": scene.get("file", {}).get("size"),
                "height": scene.get("file", {}).get("height"),
                "width": scene.get("file", {}).get("width"),
                "framerate": scene.get("file", {}).get("framerate"),
                "bitrate": scene.get("file", {}).get("bitrate"),
                "codec": scene.get("file", {}).get("video_codec"),
                "paths": scene.get("paths", []),
                "stash_created_at": scene.get("created_at", datetime.utcnow()),
                "stash_updated_at": scene.get("updated_at", datetime.utcnow()),
                "last_synced": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            scene_data.append(scene_dict)

        # Use PostgreSQL's ON CONFLICT for upsert
        stmt = insert(Scene).values(scene_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "title": stmt.excluded.title,
                "details": stmt.excluded.details,
                "url": stmt.excluded.url,
                "rating": stmt.excluded.rating,
                "organized": stmt.excluded.organized,
                "duration": stmt.excluded.duration,
                "size": stmt.excluded.size,
                "height": stmt.excluded.height,
                "width": stmt.excluded.width,
                "framerate": stmt.excluded.framerate,
                "bitrate": stmt.excluded.bitrate,
                "codec": stmt.excluded.codec,
                "paths": stmt.excluded.paths,
                "stash_updated_at": stmt.excluded.stash_updated_at,
                "last_synced": stmt.excluded.last_synced,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        db.execute(stmt)
        db.flush()

        # Fetch the upserted scenes
        scene_ids = [s["id"] for s in scene_data]
        return db.query(Scene).filter(Scene.id.in_(scene_ids)).all()

    def _prepare_entity_data(
        self, model_class: Type[BaseModel], entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare entity data based on model type"""
        if model_class == Performer:
            return self._prepare_performer_data(entities)
        elif model_class == Tag:
            return self._prepare_tag_data(entities)
        elif model_class == Studio:
            return self._prepare_studio_data(entities)
        else:
            raise ValueError(f"Unsupported model class: {model_class}")

    def _upsert_single_entity(
        self, model_class: Type[BaseModel], entity_dict: Dict[str, Any], db: Session
    ) -> bool:
        """Upsert a single entity and return True if upserted"""
        entity_id = entity_dict["id"]
        existing = db.query(model_class).filter(model_class.id == entity_id).first()

        if existing:
            # Update existing entity
            for key, value in entity_dict.items():
                if key not in ("id", "created_at"):
                    setattr(existing, key, value)
        else:
            # Create new entity
            new_entity = model_class(**entity_dict)
            db.add(new_entity)

        return True

    def bulk_upsert_entities(
        self, model_class: Type[BaseModel], entities: List[Dict[str, Any]], db: Session
    ) -> int:
        """Generic bulk upsert for entities"""
        if not entities:
            return 0

        entity_data = self._prepare_entity_data(model_class, entities)
        upserted_count = sum(
            self._upsert_single_entity(model_class, entity_dict, db)
            for entity_dict in entity_data
        )

        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise

        return upserted_count

    def get_last_sync_time(self, entity_type: str, db: Session) -> Optional[datetime]:
        """Get last successful sync time for an entity type"""
        last_sync = (
            db.query(SyncHistory)
            .filter(
                and_(
                    SyncHistory.entity_type == entity_type,
                    SyncHistory.status == "completed",
                )
            )
            .order_by(SyncHistory.completed_at.desc())
            .first()
        )

        return last_sync.completed_at if last_sync else None  # type: ignore[return-value]

    def create_sync_history(
        self, entity_type: str, job_id: str, db: Session
    ) -> SyncHistory:
        """Create a new sync history record"""
        sync_history = SyncHistory(
            entity_type=entity_type,
            job_id=job_id,
            started_at=datetime.utcnow(),
            status="in_progress",
        )
        db.add(sync_history)
        db.flush()
        return sync_history

    def update_sync_history(
        self, sync_history_id: int, status: str, stats: Dict[str, Any], db: Session
    ) -> None:
        """Update sync history with results"""
        sync_history = (
            db.query(SyncHistory).filter(SyncHistory.id == sync_history_id).first()
        )

        if sync_history:
            sync_history.status = status  # type: ignore[assignment]
            sync_history.completed_at = datetime.utcnow()  # type: ignore[assignment]
            sync_history.items_synced = stats.get("processed", 0)
            sync_history.items_created = stats.get("created", 0)
            sync_history.items_updated = stats.get("updated", 0)
            sync_history.items_failed = stats.get("failed", 0)
            sync_history.error_details = stats.get("errors", [])
            db.flush()

    def mark_entity_synced(self, entity: Any, db: Session) -> None:
        """Update last_synced timestamp for an entity"""
        entity.last_synced = datetime.utcnow()
        db.flush()

    def get_entities_needing_sync(
        self,
        model_class: Type[BaseModel],
        since: Optional[datetime],
        limit: int,
        db: Session,
    ) -> List[Any]:
        """Get entities that need syncing based on last_synced time"""
        query = db.query(model_class)

        if since:
            query = query.filter(
                or_(model_class.last_synced.is_(None), model_class.last_synced < since)
            )
        else:
            query = query.filter(model_class.last_synced.is_(None))

        return query.limit(limit).all()

    def _prepare_performer_data(
        self, performers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare performer data for bulk insert"""
        prepared_data = []
        for p in performers:
            performer_id = p.get("id")
            # Skip performers with None or empty ID to avoid SQLAlchemy warning
            if performer_id is None:
                logger.warning("Skipping performer with None ID")
                continue

            prepared_data.append(
                {
                    "id": performer_id,
                    "name": p.get("name", ""),
                    "aliases": p.get("aliases"),
                    "gender": p.get("gender"),
                    "birthdate": p.get("birthdate"),
                    "country": p.get("country"),
                    "ethnicity": p.get("ethnicity"),
                    "hair_color": p.get("hair_color"),
                    "eye_color": p.get("eye_color"),
                    "height_cm": p.get("height"),
                    "weight_kg": p.get("weight"),
                    "measurements": p.get("measurements"),
                    "fake_tits": p.get("fake_tits"),
                    "career_length": p.get("career_length"),
                    "tattoos": p.get("tattoos"),
                    "piercings": p.get("piercings"),
                    "url": p.get("url"),
                    "twitter": p.get("twitter"),
                    "instagram": p.get("instagram"),
                    "details": p.get("details"),
                    "rating": p.get("rating"),
                    "favorite": p.get("favorite", False),
                    "ignore_auto_tag": p.get("ignore_auto_tag", False),
                    "image_url": p.get("image_path"),
                    "last_synced": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        return prepared_data

    def _prepare_tag_data(self, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare tag data for bulk insert"""
        prepared_data = []
        for t in tags:
            tag_id = t.get("id")
            # Skip tags with None or empty ID
            if tag_id is None:
                logger.warning("Skipping tag with None ID")
                continue

            prepared_data.append(
                {
                    "id": tag_id,
                    "name": t.get("name", ""),
                    "aliases": t.get("aliases"),
                    "description": t.get("description"),
                    "ignore_auto_tag": t.get("ignore_auto_tag", False),
                    "parent_temp_id": (
                        t.get("parent", {}).get("id") if t.get("parent") else None
                    ),
                    "last_synced": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        return prepared_data

    def _prepare_studio_data(
        self, studios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare studio data for bulk insert"""
        prepared_data = []
        for s in studios:
            studio_id = s.get("id")
            # Skip studios with None or empty ID
            if studio_id is None:
                logger.warning("Skipping studio with None ID")
                continue

            prepared_data.append(
                {
                    "id": studio_id,
                    "name": s.get("name", ""),
                    "aliases": s.get("aliases"),
                    "url": s.get("url"),
                    "details": s.get("details"),
                    "rating": s.get("rating"),
                    "favorite": s.get("favorite", False),
                    "ignore_auto_tag": s.get("ignore_auto_tag", False),
                    "parent_temp_id": (
                        s.get("parent", {}).get("id") if s.get("parent") else None
                    ),
                    "image_url": s.get("image_path"),
                    "last_synced": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        return prepared_data
