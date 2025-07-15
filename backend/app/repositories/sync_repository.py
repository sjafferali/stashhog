import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import insert
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
                "stash_id": scene["id"],
                "title": scene.get("title", ""),
                "details": scene.get("details"),
                "url": scene.get("url"),
                "date": scene.get("date"),
                "rating": scene.get("rating"),
                "organized": scene.get("organized", False),
                "duration": scene.get("file", {}).get("duration"),
                "size": scene.get("file", {}).get("size"),
                "height": scene.get("file", {}).get("height"),
                "width": scene.get("file", {}).get("width"),
                "framerate": scene.get("file", {}).get("framerate"),
                "bitrate": scene.get("file", {}).get("bitrate"),
                "codec": scene.get("file", {}).get("video_codec"),
                "last_synced": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            scene_data.append(scene_dict)

        # Use PostgreSQL's ON CONFLICT for upsert
        stmt = insert(Scene).values(scene_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["stash_id"],
            set_={
                "title": stmt.excluded.title,
                "details": stmt.excluded.details,
                "url": stmt.excluded.url,
                "date": stmt.excluded.date,
                "rating": stmt.excluded.rating,
                "organized": stmt.excluded.organized,
                "duration": stmt.excluded.duration,
                "size": stmt.excluded.size,
                "height": stmt.excluded.height,
                "width": stmt.excluded.width,
                "framerate": stmt.excluded.framerate,
                "bitrate": stmt.excluded.bitrate,
                "codec": stmt.excluded.codec,
                "last_synced": stmt.excluded.last_synced,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        db.execute(stmt)
        db.flush()

        # Fetch the upserted scenes
        scene_ids = [s["stash_id"] for s in scene_data]
        return db.query(Scene).filter(Scene.stash_id.in_(scene_ids)).all()

    def bulk_upsert_entities(
        self, model_class: Type[BaseModel], entities: List[Dict[str, Any]], db: Session
    ) -> int:
        """Generic bulk upsert for entities"""
        if not entities:
            return 0

        # Prepare data based on model type
        if model_class == Performer:
            entity_data = self._prepare_performer_data(entities)
        elif model_class == Tag:
            entity_data = self._prepare_tag_data(entities)
        elif model_class == Studio:
            entity_data = self._prepare_studio_data(entities)
        else:
            raise ValueError(f"Unsupported model class: {model_class}")

        # Bulk upsert
        stmt = insert(model_class).values(entity_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["stash_id"],
            set_={
                col.name: getattr(stmt.excluded, col.name)
                for col in model_class.__table__.columns
                if col.name not in ["id", "stash_id", "created_at"]
            },
        )

        result = db.execute(stmt)
        db.flush()

        return result.rowcount

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
        return [
            {
                "stash_id": p["id"],
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
            for p in performers
        ]

    def _prepare_tag_data(self, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare tag data for bulk insert"""
        return [
            {
                "stash_id": t["id"],
                "name": t.get("name", ""),
                "aliases": t.get("aliases"),
                "description": t.get("description"),
                "ignore_auto_tag": t.get("ignore_auto_tag", False),
                "parent_stash_id": (
                    t.get("parent", {}).get("id") if t.get("parent") else None
                ),
                "last_synced": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            for t in tags
        ]

    def _prepare_studio_data(
        self, studios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare studio data for bulk insert"""
        return [
            {
                "stash_id": s["id"],
                "name": s.get("name", ""),
                "aliases": s.get("aliases"),
                "url": s.get("url"),
                "details": s.get("details"),
                "rating": s.get("rating"),
                "favorite": s.get("favorite", False),
                "ignore_auto_tag": s.get("ignore_auto_tag", False),
                "parent_stash_id": (
                    s.get("parent", {}).get("id") if s.get("parent") else None
                ),
                "image_url": s.get("image_path"),
                "last_synced": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            for s in studios
        ]
