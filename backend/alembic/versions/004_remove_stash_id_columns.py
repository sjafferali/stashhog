"""Remove redundant stash_id columns

Revision ID: 004
Revises: 003
Create Date: 2025-07-16

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove stash_id columns from all tables"""
    # Drop stash_id column from performer table
    op.drop_index("ix_performer_stash_id", table_name="performer")
    op.drop_column("performer", "stash_id")

    # Drop stash_id column from studio table
    op.drop_index("ix_studio_stash_id", table_name="studio")
    op.drop_column("studio", "stash_id")

    # Drop stash_id column from tag table
    op.drop_index("ix_tag_stash_id", table_name="tag")
    op.drop_column("tag", "stash_id")

    # Drop stash_id column from scene table
    op.drop_index("ix_scene_stash_id", table_name="scene")
    op.drop_column("scene", "stash_id")

    # Rename parent_stash_id to parent_temp_id in studio table
    op.alter_column("studio", "parent_stash_id", new_column_name="parent_temp_id")

    # Rename parent_stash_id to parent_temp_id in tag table
    op.alter_column("tag", "parent_stash_id", new_column_name="parent_temp_id")


def downgrade() -> None:
    """Re-add stash_id columns to all tables"""
    # Re-add stash_id to performer table
    op.add_column("performer", sa.Column("stash_id", sa.String(), nullable=False))
    op.create_index("ix_performer_stash_id", "performer", ["stash_id"], unique=True)

    # Re-add stash_id to studio table
    op.add_column("studio", sa.Column("stash_id", sa.String(), nullable=False))
    op.create_index("ix_studio_stash_id", "studio", ["stash_id"], unique=True)

    # Re-add stash_id to tag table
    op.add_column("tag", sa.Column("stash_id", sa.String(), nullable=False))
    op.create_index("ix_tag_stash_id", "tag", ["stash_id"], unique=True)

    # Re-add stash_id to scene table
    op.add_column("scene", sa.Column("stash_id", sa.String(), nullable=False))
    op.create_index("ix_scene_stash_id", "scene", ["stash_id"], unique=True)

    # Rename parent_temp_id back to parent_stash_id in studio table
    op.alter_column("studio", "parent_temp_id", new_column_name="parent_stash_id")

    # Rename parent_temp_id back to parent_stash_id in tag table
    op.alter_column("tag", "parent_temp_id", new_column_name="parent_stash_id")

    # Copy id values back to stash_id
    op.execute("UPDATE performer SET stash_id = id")
    op.execute("UPDATE studio SET stash_id = id")
    op.execute("UPDATE tag SET stash_id = id")
    op.execute("UPDATE scene SET stash_id = id")
