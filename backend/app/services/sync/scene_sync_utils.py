"""Shared utilities for syncing scenes between Stash and the database."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Performer, Scene, Studio, Tag
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


class SceneSyncUtils:
    """Utility class for syncing scene data between Stash and the database."""

    def __init__(self, stash_service: StashService):
        self.stash_service = stash_service

    async def sync_scenes_by_ids(
        self,
        scene_ids: List[str],
        db: AsyncSession,
        update_existing: bool = True,
    ) -> List[Scene]:
        """Sync specific scenes from Stash to the database.

        Args:
            scene_ids: List of scene IDs to sync
            db: Database session
            update_existing: Whether to update existing scenes

        Returns:
            List of synced Scene objects
        """
        synced_scenes = []

        for scene_id in scene_ids:
            try:
                # Fetch scene data from Stash
                stash_scene = await self.stash_service.get_scene(scene_id)
                if not stash_scene:
                    logger.warning(f"Scene {scene_id} not found in Stash")
                    continue

                # Sync the scene
                scene = await self.sync_single_scene(
                    stash_scene, db, update_existing=update_existing
                )
                if scene:
                    synced_scenes.append(scene)

            except Exception as e:
                logger.error(f"Failed to sync scene {scene_id}: {e}")

        return synced_scenes

    async def sync_single_scene(
        self,
        stash_scene: Dict[str, Any],
        db: AsyncSession,
        update_existing: bool = True,
    ) -> Optional[Scene]:
        """Sync a single scene from Stash data to the database.

        Args:
            stash_scene: Scene data from Stash
            db: Database session
            update_existing: Whether to update existing scenes

        Returns:
            Synced Scene object or None if failed
        """
        scene_id = stash_scene.get("id")
        if not scene_id:
            logger.error("Scene ID is missing from stash_scene data")
            return None

        # Check if scene exists
        result = await db.execute(
            select(Scene)
            .where(Scene.id == scene_id)
            .options(
                selectinload(Scene.performers),
                selectinload(Scene.tags),
                selectinload(Scene.studio),
            )
        )
        scene = result.scalar_one_or_none()

        if scene and not update_existing:
            logger.debug(f"Scene {scene_id} already exists, skipping update")
            return scene

        if not scene:
            scene = Scene(id=scene_id)
            db.add(scene)
            logger.info(f"Creating new scene {scene_id}")
        else:
            logger.info(f"Updating existing scene {scene_id}")

        # Update scene fields
        await self._update_scene_fields(scene, stash_scene)

        # Sync relationships
        await self._sync_scene_relationships(scene, stash_scene, db)

        # Update sync metadata
        scene.last_synced = datetime.utcnow()  # type: ignore[assignment]

        await db.flush()
        return scene

    async def _update_scene_fields(
        self, scene: Scene, stash_scene: Dict[str, Any]
    ) -> None:
        """Update scene fields from Stash data."""
        # Basic info
        scene.title = stash_scene.get("title", "")
        scene.details = stash_scene.get("details", "")
        scene.url = stash_scene.get("url", "")
        scene.rating = stash_scene.get("rating")  # type: ignore[assignment]
        scene.organized = stash_scene.get("organized", False)

        # File info
        file_info = stash_scene.get("file", {})
        scene.paths = stash_scene.get("paths", [])
        scene.file_path = stash_scene.get("file_path")  # type: ignore[assignment]
        scene.duration = file_info.get("duration")
        scene.size = file_info.get("size")
        scene.height = file_info.get("height")
        scene.width = file_info.get("width")
        scene.framerate = file_info.get("frame_rate")
        scene.bitrate = file_info.get("bitrate")
        scene.codec = file_info.get("video_codec")

        # Timestamps
        if created_at := stash_scene.get("created_at"):
            scene.stash_created_at = datetime.fromisoformat(  # type: ignore[assignment]
                created_at.replace("Z", "+00:00")
            )
        if updated_at := stash_scene.get("updated_at"):
            scene.stash_updated_at = datetime.fromisoformat(  # type: ignore[assignment]
                updated_at.replace("Z", "+00:00")
            )
        if scene_date := stash_scene.get("date"):
            scene.stash_date = datetime.fromisoformat(scene_date)  # type: ignore[assignment]

        # Content checksum for change detection
        content_fields = [
            scene.title,
            scene.details,
            scene.url,
            scene.rating,
            len(scene.paths),
        ]
        scene.content_checksum = str(hash(tuple(content_fields)))  # type: ignore[assignment]

    async def _sync_scene_relationships(
        self, scene: Scene, stash_scene: Dict[str, Any], db: AsyncSession
    ) -> None:
        """Sync scene relationships (studio, performers, tags)."""
        # Sync studio
        if studio_data := stash_scene.get("studio"):
            studio = await self._get_or_create_studio(studio_data, db)
            scene.studio = studio
        else:
            scene.studio = None

        # Sync performers
        scene.performers.clear()
        for performer_data in stash_scene.get("performers", []):
            performer = await self._get_or_create_performer(performer_data, db)
            if performer:
                scene.performers.append(performer)

        # Sync tags
        scene.tags.clear()
        for tag_data in stash_scene.get("tags", []):
            tag = await self._get_or_create_tag(tag_data, db)
            if tag:
                scene.tags.append(tag)

    async def _get_or_create_studio(
        self, studio_data: Dict[str, Any], db: AsyncSession
    ) -> Optional[Studio]:
        """Get or create a studio."""
        studio_id = studio_data.get("id")
        if not studio_id:
            return None

        result = await db.execute(select(Studio).where(Studio.id == studio_id))
        studio = result.scalar_one_or_none()

        if not studio:
            studio = Studio(
                id=studio_id,
                name=studio_data.get("name", ""),
                url=studio_data.get("url", ""),
                last_synced=datetime.utcnow(),
            )
            db.add(studio)
            await db.flush()

        return studio

    async def _get_or_create_performer(
        self, performer_data: Dict[str, Any], db: AsyncSession
    ) -> Optional[Performer]:
        """Get or create a performer."""
        performer_id = performer_data.get("id")
        if not performer_id:
            return None

        result = await db.execute(select(Performer).where(Performer.id == performer_id))
        performer = result.scalar_one_or_none()

        if not performer:
            performer = Performer(
                id=performer_id,
                name=performer_data.get("name", ""),
                gender=performer_data.get("gender"),
                url=performer_data.get("url", ""),
                image_url=performer_data.get("image_path", ""),
                last_synced=datetime.utcnow(),
            )
            # Add aliases
            if aliases := performer_data.get("aliases"):
                performer.aliases = aliases
            db.add(performer)
            await db.flush()

        return performer

    async def _get_or_create_tag(
        self, tag_data: Dict[str, Any], db: AsyncSession
    ) -> Optional[Tag]:
        """Get or create a tag."""
        tag_id = tag_data.get("id")
        if not tag_id:
            return None

        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        tag = result.scalar_one_or_none()

        if not tag:
            tag = Tag(
                id=tag_id,
                name=tag_data.get("name", ""),
                description=tag_data.get("description", ""),
                last_synced=datetime.utcnow(),
            )
            db.add(tag)
            await db.flush()

        return tag
