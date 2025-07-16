"""Studio model representing production studios from Stash."""

from typing import TYPE_CHECKING, List, Optional

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
    from app.models.scene import Scene


class Studio(BaseModel):
    """
    Studio model representing a production studio from Stash.

    Uses string IDs from Stash as primary keys.
    """

    # Primary key from Stash
    id = Column(String, primary_key=True, index=True)

    # Studio information
    name = Column(String, nullable=False, index=True)
    aliases = Column(JSON, nullable=True)  # List of aliases
    url = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    favorite = Column(Boolean, default=False, nullable=False)
    ignore_auto_tag = Column(Boolean, default=False, nullable=False)
    image_url = Column(String, nullable=True)

    # Hierarchy
    parent_id = Column(
        String, ForeignKey("studio.id", ondelete="SET NULL"), nullable=True
    )
    parent_temp_id = Column(String, nullable=True)  # Temporary field for sync

    # Sync tracking
    last_synced = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    scenes = relationship(
        "Scene",
        back_populates="studio",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Additional indexes for performance
    __table_args__ = (
        Index("idx_studio_name_lower", "name"),  # For case-insensitive searches
    )

    def get_scene_count(self) -> int:
        """Get the number of scenes from this studio."""
        return int(
            self.scenes.count()
            if hasattr(self.scenes, "count")
            else len(list(self.scenes))
        )

    def get_recent_scenes(self, limit: int = 10) -> List["Scene"]:
        """Get the most recent scenes from this studio."""
        return self.scenes.order_by("stash_date desc").limit(limit).all()  # type: ignore[no-any-return]

    def to_dict(
        self, exclude: Optional[set] = None, include_stats: bool = False
    ) -> dict:
        """Convert to dictionary with optional statistics."""
        data = super().to_dict(exclude)

        if include_stats:
            data["scene_count"] = self.get_scene_count()

        return data
