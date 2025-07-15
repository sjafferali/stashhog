import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models import Performer, Scene, Studio, Tag
from app.services.stash_service import StashService

from .strategies import SyncStrategy

logger = logging.getLogger(__name__)


class SceneSyncHandler:
    """Handles synchronization of scenes with all their relationships"""

    def __init__(self, stash_service: StashService, strategy: SyncStrategy):
        self.stash_service = stash_service
        self.strategy = strategy

    async def sync_scene(self, stash_scene: Dict[str, Any], db: Session) -> Scene:
        """Sync a single scene with all relationships"""
        scene_id = stash_scene.get("stash_id")
        if not scene_id:
            raise ValueError("Scene ID is required")

        logger.info(f"Syncing scene {scene_id}")

        # Find or create scene
        scene = db.query(Scene).filter(Scene.stash_id == scene_id).first()
        if not scene:
            scene = Scene(stash_id=scene_id)
            db.add(scene)
            logger.info(f"Creating new scene {scene_id}")
        else:
            logger.info(f"Updating existing scene {scene_id}")

        # Apply sync strategy to merge data
        merged_scene = await self.strategy.merge_data(scene, stash_scene)
        if merged_scene:
            scene = merged_scene

        if not scene:
            raise ValueError(f"Failed to sync scene {scene_id}")

        # Sync relationships
        await self._sync_scene_relationships(scene, stash_scene, db)

        # Update sync metadata
        scene.last_synced = datetime.utcnow()  # type: ignore[assignment]

        # Save to get ID if new
        db.flush()

        return scene

    async def sync_scene_batch(
        self, stash_scenes: List[Dict[str, Any]], db: Session
    ) -> List[Scene]:
        """Efficiently sync multiple scenes"""
        synced_scenes = []

        # Pre-fetch all entities to reduce queries
        scene_ids = [s["stash_id"] for s in stash_scenes if s.get("stash_id")]
        existing_scenes = {
            s.stash_id: s
            for s in db.query(Scene).filter(Scene.stash_id.in_(scene_ids)).all()
        }

        # Collect all entity IDs
        all_performer_ids: Set[str] = set()
        all_tag_ids: Set[str] = set()
        all_studio_ids: Set[str] = set()

        for scene_data in stash_scenes:
            all_performer_ids.update(p["id"] for p in scene_data.get("performers", []))
            all_tag_ids.update(t["id"] for t in scene_data.get("tags", []))
            if scene_data.get("studio", {}).get("stash_id"):
                all_studio_ids.add(scene_data["studio"]["id"])

        # Pre-fetch all entities
        performers_map = self._fetch_entities_map(db, Performer, all_performer_ids)
        tags_map = self._fetch_entities_map(db, Tag, all_tag_ids)
        studios_map = self._fetch_entities_map(db, Studio, all_studio_ids)

        # Process each scene
        for scene_data in stash_scenes:
            try:
                scene_id = scene_data.get("stash_id")
                if not scene_id:
                    continue

                # Get or create scene
                scene = existing_scenes.get(scene_id)
                if not scene:
                    scene = Scene(stash_id=scene_id)
                    db.add(scene)

                # Apply sync strategy
                merged_scene = await self.strategy.merge_data(scene, scene_data)
                if merged_scene:
                    scene = merged_scene

                if not scene:
                    logger.error(f"Failed to merge scene data for {scene_id}")
                    continue

                # Sync relationships using pre-fetched entities
                await self._sync_scene_relationships_batch(
                    scene, scene_data, db, performers_map, tags_map, studios_map
                )

                scene.last_synced = datetime.utcnow()  # type: ignore[assignment]
                synced_scenes.append(scene)

            except Exception as e:
                logger.error(
                    f"Failed to sync scene {scene_data.get('stash_id')}: {str(e)}"
                )
                raise

        db.flush()
        return synced_scenes

    async def _sync_scene_relationships(
        self, scene: Scene, stash_scene: Dict[str, Any], db: Session
    ) -> None:
        """Sync all relationships for a scene"""
        # Sync studio
        await self._sync_scene_studio(scene, stash_scene.get("studio"), db)

        # Sync performers
        await self._sync_scene_performers(scene, stash_scene.get("performers", []), db)

        # Sync tags
        await self._sync_scene_tags(scene, stash_scene.get("tags", []), db)

    async def _sync_scene_relationships_batch(
        self,
        scene: Scene,
        stash_scene: Dict[str, Any],
        db: Session,
        performers_map: Dict[str, Performer],
        tags_map: Dict[str, Tag],
        studios_map: Dict[str, Studio],
    ) -> None:
        """Sync relationships using pre-fetched entity maps"""
        # Sync studio
        studio_data = stash_scene.get("studio")
        if studio_data and studio_data.get("stash_id"):
            studio = studios_map.get(studio_data["id"])
            if studio:
                scene.studio = studio
                scene.studio_id = studio.id

        # Sync performers
        scene.performers.clear()
        for performer_data in stash_scene.get("performers", []):
            performer_id = performer_data.get("stash_id")
            if performer_id and performer_id in performers_map:
                scene.performers.append(performers_map[performer_id])

        # Sync tags
        scene.tags.clear()
        for tag_data in stash_scene.get("tags", []):
            tag_id = tag_data.get("stash_id")
            if tag_id and tag_id in tags_map:
                scene.tags.append(tags_map[tag_id])

    async def _sync_scene_studio(
        self, scene: Scene, studio_data: Optional[Dict[str, Any]], db: Session
    ) -> None:
        """Sync scene's studio relationship"""
        if not studio_data or not studio_data.get("stash_id"):
            scene.studio = None
            scene.studio_id = None  # type: ignore[assignment]
            return

        studio_id = studio_data["id"]
        studio = db.query(Studio).filter(Studio.stash_id == studio_id).first()

        if not studio:
            # Create minimal studio - full sync will happen in entity sync
            studio = Studio(
                stash_id=studio_id, name=studio_data.get("name", "Unknown Studio")
            )
            db.add(studio)
            db.flush()

        scene.studio = studio
        scene.studio_id = studio.id

    async def _sync_scene_performers(
        self, scene: Scene, performers_data: List[Dict[str, Any]], db: Session
    ) -> None:
        """Sync scene's performer relationships"""
        # Clear existing relationships
        scene.performers.clear()

        for performer_data in performers_data:
            performer_id = performer_data.get("stash_id")
            if not performer_id:
                continue

            performer = (
                db.query(Performer).filter(Performer.stash_id == performer_id).first()
            )

            if not performer:
                # Create minimal performer - full sync will happen in entity sync
                performer = Performer(
                    stash_id=performer_id,
                    name=performer_data.get("name", "Unknown Performer"),
                )
                db.add(performer)
                db.flush()

            scene.performers.append(performer)

    async def _sync_scene_tags(
        self, scene: Scene, tags_data: List[Dict[str, Any]], db: Session
    ) -> None:
        """Sync scene's tag relationships"""
        # Clear existing relationships
        scene.tags.clear()

        for tag_data in tags_data:
            tag_id = tag_data.get("stash_id")
            if not tag_id:
                continue

            tag = db.query(Tag).filter(Tag.stash_id == tag_id).first()

            if not tag:
                # Create minimal tag - full sync will happen in entity sync
                tag = Tag(stash_id=tag_id, name=tag_data.get("name", "Unknown Tag"))
                db.add(tag)
                db.flush()

            scene.tags.append(tag)

    def _fetch_entities_map(
        self, db: Session, model_class: type, entity_ids: Set[str]
    ) -> Dict[str, Any]:
        """Fetch entities by stash_id and return as a map"""
        if not entity_ids:
            return {}

        entities: List[Any] = (
            db.query(model_class).filter(model_class.stash_id.in_(entity_ids)).all()  # type: ignore[attr-defined]
        )

        return {entity.stash_id: entity for entity in entities}

    def _merge_scene_data(self, existing: Scene, stash_data: Dict[str, Any]) -> Scene:
        """Merge Stash data into existing scene"""
        # This is now handled by the sync strategy
        return existing
