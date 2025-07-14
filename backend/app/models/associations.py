"""Association tables for many-to-many relationships."""
from sqlalchemy import Table, Column, String, ForeignKey, UniqueConstraint, Index

from app.core.database import Base

# Scene-Performer association table
scene_performer = Table(
    "scene_performer",
    Base.metadata,
    Column("scene_id", String, ForeignKey("scene.id", ondelete="CASCADE"), primary_key=True),
    Column("performer_id", String, ForeignKey("performer.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("scene_id", "performer_id", name="uq_scene_performer"),
    Index("idx_scene_performer_scene", "scene_id"),
    Index("idx_scene_performer_performer", "performer_id"),
)

# Scene-Tag association table
scene_tag = Table(
    "scene_tag",
    Base.metadata,
    Column("scene_id", String, ForeignKey("scene.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("scene_id", "tag_id", name="uq_scene_tag"),
    Index("idx_scene_tag_scene", "scene_id"),
    Index("idx_scene_tag_tag", "tag_id"),
)