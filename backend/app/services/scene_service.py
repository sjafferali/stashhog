"""Service for managing scene updates in both stashhog and Stash."""

import logging
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene import Scene
from app.models.tag import Tag
from app.repositories.tag_repository import TagRepository
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


class SceneService:
    """Service class for managing scene operations across stashhog and Stash."""

    def __init__(self, stash_service: StashService):
        """Initialize the scene service.

        Args:
            stash_service: StashService instance for Stash API operations
        """
        self.stash_service = stash_service
        self.tag_repository = TagRepository()

    async def update_scene_with_sync(
        self,
        scene_id: str,
        updates: Dict[str, Any],
        db: AsyncSession,
    ) -> bool:
        """Update a scene in both stashhog database and Stash.

        This method ensures that updates are applied to both systems,
        maintaining consistency between stashhog and Stash.

        Args:
            scene_id: The scene ID to update
            updates: Dictionary of updates to apply
            db: Database session

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # First, update the scene in stashhog database
            success = await self._update_scene_in_database(scene_id, updates, db)
            if not success:
                logger.error(f"Failed to update scene {scene_id} in stashhog database")
                return False

            # Then, update the scene in Stash
            success = await self._update_scene_in_stash(scene_id, updates)
            if not success:
                logger.error(f"Failed to update scene {scene_id} in Stash")
                # Note: We don't rollback the database update here
                # This is a design decision - database is source of truth
                return False

            logger.info(f"Successfully updated scene {scene_id} in both systems")
            return True

        except Exception as e:
            logger.error(f"Error updating scene {scene_id}: {e}")
            return False

    async def _update_scene_in_database(
        self,
        scene_id: str,
        updates: Dict[str, Any],
        db: AsyncSession,
    ) -> bool:
        """Update a scene in the stashhog database.

        Args:
            scene_id: The scene ID to update
            updates: Dictionary of updates to apply
            db: Database session

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Fetch the scene
            stmt = select(Scene).where(Scene.id == scene_id)
            result = await db.execute(stmt)
            scene = result.scalars().first()

            if not scene:
                logger.error(f"Scene {scene_id} not found in database")
                return False

            # Handle special fields
            if "tag_ids" in updates:
                await self._update_scene_tags(scene, updates["tag_ids"], db)
                # Remove tag_ids from updates as it's handled separately
                updates = {k: v for k, v in updates.items() if k != "tag_ids"}

            # Apply other updates
            for key, value in updates.items():
                if hasattr(scene, key):
                    setattr(scene, key, value)

            # Handle specific attributes that need special processing
            if "video_analyzed" in updates:
                scene.video_analyzed = updates["video_analyzed"]

            await db.flush()
            logger.debug(f"Updated scene {scene_id} in database")
            return True

        except Exception as e:
            logger.error(f"Error updating scene {scene_id} in database: {e}")
            return False

    async def _update_scene_tags(
        self,
        scene: Scene,
        tag_ids: List[str],
        db: AsyncSession,
    ) -> None:
        """Update scene tags in the database.

        Args:
            scene: Scene object to update
            tag_ids: List of tag IDs to set
            db: Database session
        """
        # Clear existing tags
        scene.tags = []

        # Add new tags
        if tag_ids:
            stmt = select(Tag).where(Tag.id.in_(tag_ids))
            result = await db.execute(stmt)
            tags = result.scalars().all()
            scene.tags = list(tags)

        logger.debug(f"Updated tags for scene {scene.id}: {len(scene.tags)} tags")

    async def _update_scene_in_stash(
        self,
        scene_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a scene in Stash via API.

        Args:
            scene_id: The scene ID to update
            updates: Dictionary of updates to apply

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Use the existing stash service method
            result = await self.stash_service.update_scene(scene_id, updates)
            return result is not None
        except Exception as e:
            logger.error(f"Error updating scene {scene_id} in Stash: {e}")
            return False

    async def apply_tags_to_scene(
        self,
        scene_id: str,
        scene_data: Dict[str, Any],
        tags_to_add: List[str],
        has_tagme: bool,
        db: AsyncSession,
    ) -> int:
        """Apply tags to a scene in both systems.

        This replaces the _apply_tags_to_scene method in analysis_service.py
        to ensure both systems are updated.

        Args:
            scene_id: Scene ID to update
            scene_data: Current scene data
            tags_to_add: List of tag names to add
            has_tagme: Whether the scene has AI_TagMe tag
            db: Database session

        Returns:
            Number of new tags added
        """
        # Get existing tag IDs
        current_tags = scene_data.get("tags", [])
        existing_tag_ids = [t.get("id") for t in current_tags if t.get("id")]

        # Get IDs for new tags (create if needed)
        new_tag_ids = []
        for tag_name in tags_to_add:
            tag_id = await self.stash_service.find_or_create_tag(tag_name, db)
            if tag_id and tag_id not in existing_tag_ids:
                new_tag_ids.append(tag_id)

        if not new_tag_ids:
            return 0

        # Update scene with all tags
        all_tag_ids = existing_tag_ids + new_tag_ids

        # Remove AI_TagMe if present, add AI_Tagged
        if has_tagme:
            tagme_id = await self.stash_service.find_or_create_tag("AI_TagMe", db)
            if tagme_id in all_tag_ids:
                all_tag_ids.remove(tagme_id)

        # Add AI_Tagged
        tagged_id = await self.stash_service.find_or_create_tag("AI_Tagged", db)
        if tagged_id not in all_tag_ids:
            all_tag_ids.append(tagged_id)

        # Update scene in both systems
        updates = {"tag_ids": all_tag_ids}
        await self.update_scene_with_sync(scene_id, updates, db)

        return len(new_tag_ids)

    async def mark_scene_as_video_analyzed(
        self,
        scene_id: str,
        db: AsyncSession,
    ) -> bool:
        """Mark a scene as video analyzed in both systems.

        Args:
            scene_id: Scene ID to update
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        updates = {"video_analyzed": True}
        return await self.update_scene_with_sync(scene_id, updates, db)
