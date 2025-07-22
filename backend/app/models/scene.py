"""Scene model representing media files from Stash."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
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
    from app.models.performer import Performer  # noqa: F401
    from app.models.plan_change import PlanChange  # noqa: F401
    from app.models.scene_file import SceneFile  # noqa: F401
    from app.models.scene_marker import SceneMarker  # noqa: F401
    from app.models.studio import Studio  # noqa: F401
    from app.models.tag import Tag  # noqa: F401


class Scene(BaseModel):
    """
    Scene model representing a media file from Stash.

    Uses string IDs from Stash as primary keys.
    """

    # Primary key from Stash
    id = Column(String, primary_key=True, index=True)

    # Basic scene information
    title = Column(String, nullable=False, index=True)
    organized = Column(Boolean, default=False, nullable=False, index=True)
    analyzed = Column(Boolean, default=False, nullable=False, index=True)
    video_analyzed = Column(Boolean, default=False, nullable=False, index=True)
    details = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)

    # Date fields
    # Stash-sourced timestamps (prefixed with stash_ for clarity)
    stash_created_at = Column(DateTime(timezone=True), nullable=False)
    stash_updated_at = Column(DateTime(timezone=True), nullable=True)
    stash_date = Column(DateTime(timezone=True), nullable=True, index=True)

    # Foreign keys
    studio_id = Column(
        String, ForeignKey("studio.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Sync tracking
    last_synced = Column(DateTime(timezone=True), nullable=False, index=True)
    content_checksum = Column(String, nullable=True)  # For smart sync strategy

    # Relationships
    studio = relationship("Studio", back_populates="scenes", lazy="joined")
    performers = relationship(
        "Performer",
        secondary="scene_performer",
        back_populates="scenes",
        lazy="selectin",
    )
    tags = relationship(
        "Tag", secondary="scene_tag", back_populates="scenes", lazy="selectin"
    )
    plan_changes = relationship(
        "PlanChange",
        back_populates="scene",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    markers = relationship(
        "SceneMarker",
        back_populates="scene",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    files = relationship(
        "SceneFile",
        back_populates="scene",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_scene_organized_date", "organized", "stash_date"),
        Index("idx_scene_studio_date", "studio_id", "stash_date"),
        Index("idx_scene_sync_status", "last_synced", "organized"),
        Index("idx_scene_analyzed", "analyzed"),
        Index("idx_scene_analyzed_organized", "analyzed", "organized"),
    )

    def add_performer(self, performer: "Performer") -> None:
        """Add a performer to the scene."""
        if performer not in self.performers:
            self.performers.append(performer)

    def remove_performer(self, performer: "Performer") -> None:
        """Remove a performer from the scene."""
        if performer in self.performers:
            self.performers.remove(performer)

    def add_tag(self, tag: "Tag") -> None:
        """Add a tag to the scene."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: "Tag") -> None:
        """Remove a tag from the scene."""
        if tag in self.tags:
            self.tags.remove(tag)

    def get_primary_path(self) -> Optional[str]:
        """Get the primary file path for the scene."""
        primary_file = self.get_primary_file()
        return primary_file.path if primary_file else None  # type: ignore[return-value]

    def get_primary_file(self) -> Optional["SceneFile"]:
        """Get the primary file for this scene."""
        if not hasattr(self, "files") or not self.files:
            return None
        return next(
            (f for f in self.files if f.is_primary),
            self.files[0] if self.files else None,
        )

    def to_dict(self, exclude: Optional[set] = None) -> dict:
        """Convert to dictionary with relationships."""
        data = super().to_dict(exclude)

        # Add relationship data
        if hasattr(self, "studio") and self.studio:
            data["studio"] = {"id": self.studio.id, "name": self.studio.name}

        if hasattr(self, "performers"):
            data["performers"] = [{"id": p.id, "name": p.name} for p in self.performers]

        if hasattr(self, "tags"):
            data["tags"] = [{"id": t.id, "name": t.name} for t in self.tags]

        return data
