"""Repository for Tag database operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.base_logger import get_logger
from app.models.tag import Tag

logger = get_logger(__name__)


class TagRepository:
    """Repository class for Tag database operations."""

    async def find_tag_by_name(self, db: AsyncSession, name: str) -> Optional[Tag]:
        """Find a tag by name in the stashhog database.

        Args:
            db: Database session
            name: Tag name to search for

        Returns:
            Tag object if found, None otherwise
        """
        try:
            stmt = select(Tag).where(Tag.name == name)
            result = await db.execute(stmt)
            tag = result.scalars().first()

            if tag:
                logger.debug(
                    f"Found tag '{name}' in stashhog database with id: {tag.id}"
                )
            else:
                logger.debug(f"Tag '{name}' not found in stashhog database")

            return tag
        except Exception as e:
            logger.error(f"Error finding tag by name '{name}': {e}")
            return None

    async def find_tag_by_id(self, db: AsyncSession, tag_id: str) -> Optional[Tag]:
        """Find a tag by ID in the stashhog database.

        Args:
            db: Database session
            tag_id: Tag ID to search for

        Returns:
            Tag object if found, None otherwise
        """
        try:
            stmt = select(Tag).where(Tag.id == tag_id)
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error finding tag by id '{tag_id}': {e}")
            return None

    async def get_all_tags(self, db: AsyncSession) -> List[Tag]:
        """Get all tags from the stashhog database.

        Args:
            db: Database session

        Returns:
            List of all tags
        """
        try:
            stmt = select(Tag).order_by(Tag.name)
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all tags: {e}")
            return []

    async def create_or_update_tag(
        self, db: AsyncSession, tag_data: dict
    ) -> Optional[Tag]:
        """Create or update a tag in the stashhog database.

        Args:
            db: Database session
            tag_data: Dictionary containing tag data (must include 'id' and 'name')

        Returns:
            Created or updated Tag object
        """
        try:
            tag_id = tag_data.get("id")
            if not tag_id:
                logger.error("Cannot create tag without ID")
                return None

            # Check if tag exists
            existing = await self.find_tag_by_id(db, tag_id)

            if existing:
                # Update existing tag
                for key, value in tag_data.items():
                    setattr(existing, key, value)
                tag = existing
                logger.debug(f"Updated existing tag '{tag.name}' with id: {tag.id}")
            else:
                # Create new tag
                tag = Tag(**tag_data)
                db.add(tag)
                logger.debug(f"Created new tag '{tag.name}' with id: {tag.id}")

            await db.flush()
            return tag
        except Exception as e:
            logger.error(f"Error creating/updating tag: {e}")
            return None

    async def find_tags_by_names(self, db: AsyncSession, names: List[str]) -> List[Tag]:
        """Find multiple tags by their names.

        Args:
            db: Database session
            names: List of tag names to search for

        Returns:
            List of found tags
        """
        try:
            if not names:
                return []

            stmt = select(Tag).where(Tag.name.in_(names))
            result = await db.execute(stmt)
            tags = list(result.scalars().all())

            logger.debug(f"Found {len(tags)} tags out of {len(names)} requested")
            return tags
        except Exception as e:
            logger.error(f"Error finding tags by names: {e}")
            return []

    def find_tag_by_name_sync(self, db: Session, name: str) -> Optional[Tag]:
        """Synchronous version of find_tag_by_name for non-async contexts.

        Args:
            db: Database session
            name: Tag name to search for

        Returns:
            Tag object if found, None otherwise
        """
        try:
            stmt = select(Tag).where(Tag.name == name)
            result = db.execute(stmt)
            tag = result.scalars().first()

            if tag:
                logger.debug(
                    f"Found tag '{name}' in stashhog database with id: {tag.id}"
                )
            else:
                logger.debug(f"Tag '{name}' not found in stashhog database")

            return tag
        except Exception as e:
            logger.error(f"Error finding tag by name '{name}': {e}")
            return None
