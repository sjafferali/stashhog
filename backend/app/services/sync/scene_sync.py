import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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

    async def sync_scene(
        self, stash_scene: Dict[str, Any], db: Union[Session, AsyncSession]
    ) -> Scene:
        """Sync a single scene with all relationships"""
        scene_id = self._validate_scene_id(stash_scene)
        logger.info(f"Syncing scene {scene_id}")

        # Find or create scene
        scene = await self._find_or_create_scene(scene_id, db)

        # Apply sync strategy to merge data
        scene = await self._apply_sync_strategy(scene, stash_scene, scene_id)

        # Sync relationships
        await self._sync_relationships_with_logging(scene, stash_scene, db, scene_id)

        # Update metadata and save
        await self._finalize_scene_sync(scene, db, scene_id)

        return scene

    def _validate_scene_id(self, stash_scene: Dict[str, Any]) -> str:
        """Validate and extract scene ID from stash data"""
        scene_id = stash_scene.get("id")
        logger.debug(f"sync_scene called with scene_id: {scene_id}")
        logger.debug(
            f"stash_scene keys: {list(stash_scene.keys()) if stash_scene else 'None'}"
        )
        if not scene_id:
            logger.error("Scene ID is missing from stash_scene data")
            raise ValueError("Scene ID is required")
        return str(scene_id)

    async def _find_or_create_scene(
        self, scene_id: str, db: Union[Session, AsyncSession]
    ) -> Scene:
        """Find existing scene or create new one"""
        logger.debug(f"Querying database for scene {scene_id}")
        stmt = select(Scene).where(Scene.id == scene_id)
        if isinstance(db, AsyncSession):
            result = await db.execute(stmt)
            scene = result.scalar_one_or_none()
        else:
            result = db.execute(stmt)
            scene = result.scalar_one_or_none()

        if not scene:
            logger.debug(f"Scene {scene_id} not found, creating new scene")
            scene = Scene(id=scene_id)
            db.add(scene)
            logger.info(f"Creating new scene {scene_id}")
        else:
            logger.debug(f"Scene {scene_id} found in database")
            logger.info(f"Updating existing scene {scene_id}")

        return scene

    async def _apply_sync_strategy(
        self, scene: Scene, stash_scene: Dict[str, Any], scene_id: str
    ) -> Scene:
        """Apply sync strategy to merge scene data"""
        logger.debug(f"Applying sync strategy to merge data for scene {scene_id}")
        try:
            merged_scene = await self.strategy.merge_data(scene, stash_scene)
            logger.debug(f"Strategy merge_data returned: {merged_scene is not None}")
            if merged_scene:
                scene = merged_scene
                logger.debug("Using merged scene data")
            else:
                logger.warning(
                    f"Strategy merge_data returned None for scene {scene_id}"
                )
        except Exception as e:
            logger.error(f"Error in strategy.merge_data for scene {scene_id}: {str(e)}")
            logger.debug(
                f"merge_data exception type: {type(e).__name__}, value: {repr(e)}"
            )
            raise

        if not scene:
            logger.error(f"Scene object is None after merge for scene_id {scene_id}")
            raise ValueError(f"Failed to sync scene {scene_id}")

        return scene

    async def _sync_relationships_with_logging(
        self,
        scene: Scene,
        stash_scene: Dict[str, Any],
        db: Union[Session, AsyncSession],
        scene_id: str,
    ) -> None:
        """Sync scene relationships with error handling and logging"""
        logger.debug(f"Syncing relationships for scene {scene_id}")
        try:
            await self._sync_scene_relationships(scene, stash_scene, db)
            logger.debug(f"Relationships synced successfully for scene {scene_id}")
        except Exception as e:
            logger.error(f"Error syncing relationships for scene {scene_id}: {str(e)}")
            logger.debug(
                f"Relationship sync exception: {type(e).__name__}, value: {repr(e)}"
            )
            raise

    async def _finalize_scene_sync(
        self, scene: Scene, db: Union[Session, AsyncSession], scene_id: str
    ) -> None:
        """Update metadata and flush to database"""
        scene.last_synced = datetime.utcnow()  # type: ignore[assignment]
        logger.debug(f"Updated last_synced for scene {scene_id}")

        logger.debug(f"Flushing database for scene {scene_id}")
        if isinstance(db, AsyncSession):
            await db.flush()
        else:
            db.flush()
        logger.debug(f"Scene {scene_id} flushed to database successfully")

    async def sync_scene_batch(
        self, stash_scenes: List[Dict[str, Any]], db: Union[Session, AsyncSession]
    ) -> List[Scene]:
        """Efficiently sync multiple scenes"""
        synced_scenes: List[Scene] = []

        # Pre-fetch existing scenes
        existing_scenes = await self._fetch_existing_scenes(stash_scenes, db)

        # Collect and pre-fetch all related entities
        entity_maps = await self._prefetch_all_entities(stash_scenes, db)

        # Process each scene
        for scene_data in stash_scenes:
            scene = await self._process_batch_scene(
                scene_data, db, existing_scenes, entity_maps, synced_scenes
            )
            if scene:
                synced_scenes.append(scene)

        # Flush all changes
        await self._flush_database(db)
        return synced_scenes

    async def _fetch_existing_scenes(
        self, stash_scenes: List[Dict[str, Any]], db: Union[Session, AsyncSession]
    ) -> Dict[str, Scene]:
        """Fetch existing scenes from database"""
        scene_ids = [s["id"] for s in stash_scenes if s.get("id")]
        stmt = select(Scene).where(Scene.id.in_(scene_ids))
        if isinstance(db, AsyncSession):
            result = await db.execute(stmt)
            scenes = result.scalars().all()
        else:
            result = db.execute(stmt)
            scenes = result.scalars().all()
        return {str(s.id): s for s in scenes}

    async def _prefetch_all_entities(
        self, stash_scenes: List[Dict[str, Any]], db: Union[Session, AsyncSession]
    ) -> Dict[str, Dict[str, Any]]:
        """Collect and pre-fetch all related entities"""
        # Collect all entity IDs
        all_performer_ids: Set[str] = set()
        all_tag_ids: Set[str] = set()
        all_studio_ids: Set[str] = set()

        for scene_data in stash_scenes:
            all_performer_ids.update(p["id"] for p in scene_data.get("performers", []))
            all_tag_ids.update(t["id"] for t in scene_data.get("tags", []))
            if scene_data.get("studio", {}).get("id"):
                all_studio_ids.add(scene_data["studio"]["id"])

        # Pre-fetch all entities
        performers_map = await self._fetch_entities_map(
            db, Performer, all_performer_ids
        )
        tags_map = await self._fetch_entities_map(db, Tag, all_tag_ids)
        studios_map = await self._fetch_entities_map(db, Studio, all_studio_ids)

        return {"performers": performers_map, "tags": tags_map, "studios": studios_map}

    async def _process_batch_scene(
        self,
        scene_data: Dict[str, Any],
        db: Union[Session, AsyncSession],
        existing_scenes: Dict[str, Scene],
        entity_maps: Dict[str, Dict[str, Any]],
        synced_scenes: List[Scene],
    ) -> Optional[Scene]:
        """Process a single scene in batch mode"""
        try:
            scene_id = scene_data.get("id")
            if not scene_id:
                return None

            # Get or create scene
            scene = existing_scenes.get(scene_id)
            if not scene:
                scene = Scene(id=scene_id)
                db.add(scene)

            # Apply sync strategy
            merged_scene = await self.strategy.merge_data(scene, scene_data)
            if merged_scene:
                scene = merged_scene

            if not scene:
                logger.error(f"Failed to merge scene data for {scene_id}")
                return None

            # Sync relationships using pre-fetched entities
            await self._sync_scene_relationships_batch(
                scene,
                scene_data,
                db,
                entity_maps["performers"],
                entity_maps["tags"],
                entity_maps["studios"],
            )

            scene.last_synced = datetime.utcnow()  # type: ignore[assignment]
            return scene

        except Exception as e:
            logger.error(f"Failed to sync scene {scene_data.get('id')}: {str(e)}")
            raise

    async def _flush_database(self, db: Union[Session, AsyncSession]) -> None:
        """Flush database changes"""
        if isinstance(db, AsyncSession):
            await db.flush()
        else:
            db.flush()

    async def _sync_scene_relationships(
        self,
        scene: Scene,
        stash_scene: Dict[str, Any],
        db: Union[Session, AsyncSession],
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
        db: Union[Session, AsyncSession],
        performers_map: Dict[str, Performer],
        tags_map: Dict[str, Tag],
        studios_map: Dict[str, Studio],
    ) -> None:
        """Sync relationships using pre-fetched entity maps"""
        # Sync studio
        studio_data = stash_scene.get("studio")
        if studio_data and studio_data.get("id"):
            studio = studios_map.get(studio_data["id"])
            if studio:
                scene.studio = studio
                scene.studio_id = studio.id

        # Sync performers
        scene.performers.clear()
        for performer_data in stash_scene.get("performers", []):
            performer_id = performer_data.get("id")
            if performer_id and performer_id in performers_map:
                scene.performers.append(performers_map[performer_id])

        # Sync tags
        scene.tags.clear()
        for tag_data in stash_scene.get("tags", []):
            tag_id = tag_data.get("id")
            if tag_id and tag_id in tags_map:
                scene.tags.append(tags_map[tag_id])

    async def _sync_scene_studio(
        self,
        scene: Scene,
        studio_data: Optional[Dict[str, Any]],
        db: Union[Session, AsyncSession],
    ) -> None:
        """Sync scene's studio relationship"""
        if not studio_data or not studio_data.get("id"):
            scene.studio = None
            scene.studio_id = None  # type: ignore[assignment]
            return

        studio_id = studio_data["id"]
        stmt = select(Studio).where(Studio.id == studio_id)
        if isinstance(db, AsyncSession):
            result = await db.execute(stmt)
            studio = result.scalar_one_or_none()
        else:
            result = db.execute(stmt)
            studio = result.scalar_one_or_none()

        if not studio:
            # Create minimal studio - full sync will happen in entity sync
            studio = Studio(
                id=studio_id,
                name=studio_data.get("name", "Unknown Studio"),
                last_synced=datetime.utcnow(),
            )
            db.add(studio)
            if isinstance(db, AsyncSession):
                await db.flush()
            else:
                db.flush()

        scene.studio = studio
        scene.studio_id = studio.id

    async def _sync_scene_performers(
        self,
        scene: Scene,
        performers_data: List[Dict[str, Any]],
        db: Union[Session, AsyncSession],
    ) -> None:
        """Sync scene's performer relationships"""
        # Clear existing relationships
        scene.performers.clear()

        for performer_data in performers_data:
            performer_id = performer_data.get("id")
            if not performer_id:
                continue

            stmt = select(Performer).where(Performer.id == performer_id)
            if isinstance(db, AsyncSession):
                result = await db.execute(stmt)
                performer = result.scalar_one_or_none()
            else:
                result = db.execute(stmt)
                performer = result.scalar_one_or_none()

            if not performer:
                # Create minimal performer - full sync will happen in entity sync
                performer = Performer(
                    id=performer_id,
                    name=performer_data.get("name", "Unknown Performer"),
                    last_synced=datetime.utcnow(),
                )
                db.add(performer)
                if isinstance(db, AsyncSession):
                    await db.flush()
                else:
                    db.flush()

            scene.performers.append(performer)

    async def _sync_scene_tags(
        self,
        scene: Scene,
        tags_data: List[Dict[str, Any]],
        db: Union[Session, AsyncSession],
    ) -> None:
        """Sync scene's tag relationships"""
        # Clear existing relationships
        scene.tags.clear()

        for tag_data in tags_data:
            tag_id = tag_data.get("id")
            if not tag_id:
                continue

            stmt = select(Tag).where(Tag.id == tag_id)
            if isinstance(db, AsyncSession):
                result = await db.execute(stmt)
                tag = result.scalar_one_or_none()
            else:
                result = db.execute(stmt)
                tag = result.scalar_one_or_none()

            if not tag:
                # Create minimal tag - full sync will happen in entity sync
                tag = Tag(
                    id=tag_id,
                    name=tag_data.get("name", "Unknown Tag"),
                    last_synced=datetime.utcnow(),
                )
                db.add(tag)
                if isinstance(db, AsyncSession):
                    await db.flush()
                else:
                    db.flush()

            scene.tags.append(tag)

    async def _fetch_entities_map(
        self, db: Union[Session, AsyncSession], model_class: type, entity_ids: Set[str]
    ) -> Dict[str, Any]:
        """Fetch entities by id and return as a map"""
        if not entity_ids:
            return {}

        stmt = select(model_class).where(model_class.id.in_(entity_ids))  # type: ignore[attr-defined, var-annotated]
        entities_list: List[Any]
        if isinstance(db, AsyncSession):
            result = await db.execute(stmt)
            entities_list = result.scalars().all()
        else:
            result = db.execute(stmt)
            entities_list = result.scalars().all()

        return {entity.id: entity for entity in entities_list}

    def _merge_scene_data(self, existing: Scene, stash_data: Dict[str, Any]) -> Scene:
        """Merge Stash data into existing scene"""
        # This is now handled by the sync strategy
        return existing
