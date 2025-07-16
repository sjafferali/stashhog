"""Add analyzed field to Scene model

Revision ID: 005
Revises: 004
Create Date: 2025-01-16

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add analyzed column to scene table
    op.add_column(
        "scene", sa.Column("analyzed", sa.Boolean(), nullable=False, server_default="0")
    )

    # Create indexes for the new field
    op.create_index("idx_scene_analyzed", "scene", ["analyzed"])
    op.create_index("idx_scene_analyzed_organized", "scene", ["analyzed", "organized"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_scene_analyzed_organized", table_name="scene")
    op.drop_index("idx_scene_analyzed", table_name="scene")

    # Drop column
    op.drop_column("scene", "analyzed")
