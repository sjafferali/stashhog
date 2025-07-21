"""fix scene markers foreign key

Revision ID: 3a905f79ec40
Revises: 148f694b2bdd
Create Date: 2025-07-21 11:44:10.588135

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a905f79ec40"
down_revision: Union[str, None] = "148f694b2bdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing tables (they're new and empty)
    op.drop_table("scene_marker_tags")
    op.drop_index("ix_scene_markers_scene_id", table_name="scene_markers")
    op.drop_table("scene_markers")

    # Recreate with correct foreign key
    op.create_table(
        "scene_markers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scene_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=True),
        sa.Column("primary_tag_id", sa.String(), nullable=False),
        sa.Column("stash_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stash_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_checksum", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["primary_tag_id"],
            ["tag.id"],
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["scene.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scene_markers_scene_id"), "scene_markers", ["scene_id"], unique=False
    )

    # Recreate scene_marker_tags association table
    op.create_table(
        "scene_marker_tags",
        sa.Column("scene_marker_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scene_marker_id"],
            ["scene_markers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tag.id"],
        ),
        sa.PrimaryKeyConstraint("scene_marker_id", "tag_id"),
    )


def downgrade() -> None:
    # Drop the fixed tables
    op.drop_table("scene_marker_tags")
    op.drop_index(op.f("ix_scene_markers_scene_id"), table_name="scene_markers")
    op.drop_table("scene_markers")

    # Recreate with incorrect foreign key (as it was)
    op.create_table(
        "scene_markers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scene_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=True),
        sa.Column("primary_tag_id", sa.String(), nullable=False),
        sa.Column("stash_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stash_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_checksum", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["primary_tag_id"],
            ["tags.id"],
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["scenes.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scene_markers_scene_id"), "scene_markers", ["scene_id"], unique=False
    )

    op.create_table(
        "scene_marker_tags",
        sa.Column("scene_marker_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scene_marker_id"],
            ["scene_markers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.PrimaryKeyConstraint("scene_marker_id", "tag_id"),
    )
