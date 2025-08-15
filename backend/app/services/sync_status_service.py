"""Service for centralized sync status checks.

This service provides a single source of truth for checking sync status,
particularly for pending scenes that need to be synced from Stash.
"""

import logging
from datetime import datetime
from typing import Optional, cast

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.models import SyncHistory
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


class SyncStatusService:
    """Service for checking sync status and pending items."""

    def __init__(self, stash_service: StashService):
        self.stash_service = stash_service

    async def get_last_sync_time(
        self, db: AsyncDBSession, entity_type: str
    ) -> Optional[datetime]:
        """Get the last successful sync time for an entity type.

        Args:
            db: Database session
            entity_type: Type of entity (scene, performer, tag, studio)

        Returns:
            Last sync datetime or None if never synced
        """
        query = (
            select(SyncHistory)
            .where(
                SyncHistory.entity_type == entity_type,
                SyncHistory.status == "completed",
            )
            .order_by(SyncHistory.completed_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        last_sync = result.scalar_one_or_none()

        if last_sync and last_sync.completed_at:
            # Type cast to help MyPy understand this is a datetime
            return cast(datetime, last_sync.completed_at)
        return None

    async def get_pending_scenes_count(
        self, db: AsyncDBSession, last_sync: Optional[datetime] = None
    ) -> int:
        """Get count of scenes pending sync from Stash.

        This is the single source of truth for determining how many scenes
        have been updated in Stash since the last sync.

        Args:
            db: Database session
            last_sync: Optional last sync datetime. If not provided, will be fetched.

        Returns:
            Count of scenes pending sync from Stash
        """
        try:
            # If last_sync not provided, fetch it
            if last_sync is None:
                last_sync = await self.get_last_sync_time(db, "scene")

            if last_sync:
                # Parse and format timestamp for Stash
                dt_no_microseconds = last_sync.replace(microsecond=0)

                # Convert to Pacific timezone for Stash filter
                pacific_tz = pytz.timezone("America/Los_Angeles")
                dt_pacific = dt_no_microseconds.astimezone(pacific_tz)
                formatted_timestamp = dt_pacific.strftime("%Y-%m-%dT%H:%M:%SZ")

                filter_dict = {
                    "updated_at": {
                        "value": formatted_timestamp,
                        "modifier": "GREATER_THAN",
                    }
                }
                logger.info(f"Checking for scenes updated after: {formatted_timestamp}")
            else:
                # No previous sync, count all scenes as pending
                filter_dict = {}
                logger.info(
                    "No previous scene sync found, counting all scenes as pending"
                )

            scenes, total_count = await self.stash_service.get_scenes(
                page=1,
                per_page=1,
                filter=filter_dict,
            )
            return total_count

        except Exception as e:
            logger.error(f"Error getting pending scenes count: {str(e)}", exc_info=True)
            return 0

    async def get_sync_status(self, db: AsyncDBSession) -> dict:
        """Get comprehensive sync status information.

        Returns:
            Dictionary containing sync status for all entity types
        """
        # Get last sync times for all entity types
        last_syncs = {}
        for entity_type in ["scene", "performer", "tag", "studio"]:
            last_sync = await self.get_last_sync_time(db, entity_type)
            if last_sync:
                last_syncs[entity_type] = last_sync.isoformat()

        # Get pending scenes count
        pending_scenes = await self.get_pending_scenes_count(db)

        return {
            "last_scene_sync": last_syncs.get("scene"),
            "last_performer_sync": last_syncs.get("performer"),
            "last_tag_sync": last_syncs.get("tag"),
            "last_studio_sync": last_syncs.get("studio"),
            "pending_scenes": pending_scenes,
        }
