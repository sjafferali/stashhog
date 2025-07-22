"""Scene file model representing individual files for a scene."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.scene import Scene  # noqa: F401


class SceneFile(BaseModel):
    """
    Scene file model representing a media file associated with a scene.

    Each scene can have multiple files (duplicates, different versions, etc).
    """

    # Primary key from Stash
    id = Column(String, primary_key=True, index=True)

    # Foreign key to scene
    scene_id = Column(
        String, ForeignKey("scene.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # File identification
    path = Column(String, nullable=False)
    basename = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)

    # File organization
    parent_folder_id = Column(String, nullable=True)
    zip_file_id = Column(String, nullable=True)

    # File properties
    mod_time = Column(DateTime(timezone=True), nullable=True)
    size = Column(BigInteger, nullable=True)  # File size in bytes
    format = Column(String, nullable=True)

    # Video properties
    width = Column(Integer, nullable=True)  # Video width in pixels
    height = Column(Integer, nullable=True)  # Video height in pixels
    duration = Column(Float, nullable=True)  # Duration in seconds
    video_codec = Column(String, nullable=True)
    audio_codec = Column(String, nullable=True)
    frame_rate = Column(Float, nullable=True)  # Frames per second
    bit_rate = Column(Integer, nullable=True)  # Bitrate in bps

    # Fingerprints
    oshash = Column(String, nullable=True, index=True)
    phash = Column(String, nullable=True)

    # Timestamps from Stash
    stash_created_at = Column(DateTime(timezone=True), nullable=True)
    stash_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Sync tracking
    last_synced = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    scene = relationship("Scene", back_populates="files")

    # Composite indexes and constraints
    __table_args__ = (
        Index("idx_scene_file_scene_primary", "scene_id", "is_primary"),
        # Ensure only one primary file per scene
        UniqueConstraint(
            "scene_id",
            "is_primary",
            name="uq_scene_file_primary",
            # This constraint only applies when is_primary is True
            # SQLAlchemy doesn't support partial unique constraints directly,
            # so we'll handle this in the migration
        ),
    )

    def to_dict(self, exclude: Optional[set] = None) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict(exclude)

        # Add computed properties
        if self.frame_rate and self.bit_rate:
            data["framerate"] = self.frame_rate  # Alias for compatibility
            data["bitrate_kbps"] = self.bit_rate // 1000  # Convert to kbps

        return data
