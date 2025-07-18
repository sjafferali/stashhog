"""Scene repository for database operations."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scene


class SceneRepository:
    """Repository for scene database operations."""

    async def get_unanalyzed_scenes(self, db: AsyncSession) -> List[Scene]:
        """Get all scenes that haven't been analyzed yet.

        Args:
            db: Database session

        Returns:
            List of unanalyzed scenes
        """
        # This is a placeholder implementation
        # In a real implementation, this would query scenes without analysis data
        stmt = select(Scene).limit(0)  # Return empty list for now
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Singleton instance
scene_repository = SceneRepository()
