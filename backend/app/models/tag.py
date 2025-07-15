"""Tag model representing content tags from Stash."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.scene import Scene  # noqa: F401


class Tag(BaseModel):
    """
    Tag model representing a content tag from Stash.

    Uses string IDs from Stash as primary keys.
    """

    # Primary key from Stash
    id = Column(String, primary_key=True, index=True)
    stash_id = Column(
        String, unique=True, nullable=False, index=True
    )  # Stash's ID for syncing

    # Tag information
    name = Column(String, nullable=False, unique=True, index=True)
    aliases = Column(JSON, nullable=True)  # List of aliases
    description = Column(Text, nullable=True)
    ignore_auto_tag = Column(Boolean, default=False, nullable=False)

    # Hierarchy
    parent_id = Column(String, ForeignKey("tag.id", ondelete="SET NULL"), nullable=True)
    parent_stash_id = Column(String, nullable=True)  # Temporary field for sync

    # Sync tracking
    last_synced = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    scenes = relationship(
        "Scene", secondary="scene_tag", back_populates="tags", lazy="dynamic"
    )

    # Additional indexes for performance
    __table_args__ = (
        Index("idx_tag_name_lower", "name"),  # For case-insensitive searches
    )

    def get_scene_count(self) -> int:
        """Get the number of scenes that have this tag."""
        return int(
            self.scenes.count()
            if hasattr(self.scenes, "count")
            else len(list(self.scenes))
        )

    def to_dict(
        self, exclude: Optional[set] = None, include_stats: bool = False
    ) -> dict:
        """Convert to dictionary with optional statistics."""
        data = super().to_dict(exclude)

        if include_stats:
            data["scene_count"] = self.get_scene_count()

        return data
