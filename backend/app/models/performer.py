"""Performer model representing actors/actresses from Stash."""
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, DateTime, Index, Boolean, Integer, Text, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.scene import Scene


class Performer(BaseModel):
    """
    Performer model representing an actor/actress from Stash.
    
    Uses string IDs from Stash as primary keys.
    """
    
    # Primary key from Stash
    id = Column(String, primary_key=True, index=True)
    stash_id = Column(String, unique=True, nullable=False, index=True)  # Stash's ID for syncing
    
    # Performer information
    name = Column(String, nullable=False, index=True)
    aliases = Column(JSON, nullable=True)  # List of aliases
    gender = Column(String, nullable=True)
    birthdate = Column(String, nullable=True)  # Date as string
    country = Column(String, nullable=True)
    ethnicity = Column(String, nullable=True)
    hair_color = Column(String, nullable=True)
    eye_color = Column(String, nullable=True)
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Integer, nullable=True)
    measurements = Column(String, nullable=True)
    fake_tits = Column(String, nullable=True)
    career_length = Column(String, nullable=True)
    tattoos = Column(Text, nullable=True)
    piercings = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    instagram = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    favorite = Column(Boolean, default=False, nullable=False)
    ignore_auto_tag = Column(Boolean, default=False, nullable=False)
    image_url = Column(String, nullable=True)
    
    # Sync tracking
    last_synced = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationships
    scenes = relationship(
        "Scene",
        secondary="scene_performer",
        back_populates="performers",
        lazy="dynamic"
    )
    
    # Additional indexes for performance
    __table_args__ = (
        Index("idx_performer_name_lower", "name"),  # For case-insensitive searches
    )
    
    def get_scene_count(self) -> int:
        """Get the number of scenes this performer appears in."""
        return self.scenes.count() if hasattr(self.scenes, "count") else len(list(self.scenes))
    
    def to_dict(self, exclude: set = None, include_stats: bool = False) -> dict:
        """Convert to dictionary with optional statistics."""
        data = super().to_dict(exclude)
        
        if include_stats:
            data["scene_count"] = self.get_scene_count()
            
        return data