"""Scene marker model for database storage."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Table
from sqlalchemy.orm import declared_attr, relationship

from app.models.base import BaseModel

scene_marker_tags = Table(
    "scene_marker_tags",
    BaseModel.metadata,
    Column("scene_marker_id", String, ForeignKey("scene_markers.id"), primary_key=True),
    Column("tag_id", String, ForeignKey("tag.id"), primary_key=True),
)


class SceneMarker(BaseModel):
    """Represents a marker/timestamp in a scene with associated tags."""

    @declared_attr  # type: ignore[arg-type]
    def __tablename__(cls) -> str:
        """Override table name to use plural form."""
        return "scene_markers"

    id = Column(String, primary_key=True)
    scene_id = Column(String, ForeignKey("scene.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=True)
    primary_tag_id = Column(String, ForeignKey("tag.id"), nullable=False)

    # Timestamps from Stash
    stash_created_at = Column(DateTime(timezone=True), nullable=True)
    stash_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Sync tracking
    last_synced = Column(DateTime(timezone=True), nullable=True)
    content_checksum = Column(String, nullable=True)

    # Relationships
    scene = relationship("Scene", back_populates="markers")
    primary_tag = relationship("Tag", foreign_keys=[primary_tag_id])
    tags = relationship("Tag", secondary=scene_marker_tags, backref="scene_markers")
