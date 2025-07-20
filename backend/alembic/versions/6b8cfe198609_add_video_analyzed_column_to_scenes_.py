"""Add video_analyzed column to scenes table

Revision ID: 6b8cfe198609
Revises: 4caf6db6de5b
Create Date: 2025-07-18 22:53:05.220997

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b8cfe198609"
down_revision: Union[str, None] = "4caf6db6de5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add video_analyzed column to scenes table
    # First add as nullable to avoid long table rewrite
    op.add_column(
        "scenes",
        sa.Column(
            "video_analyzed", sa.Boolean(), nullable=True
        ),
    )
    
    # Set default value for existing rows in batches
    op.execute("UPDATE scenes SET video_analyzed = false WHERE video_analyzed IS NULL")
    
    # Now make it NOT NULL with default
    op.alter_column(
        "scenes",
        "video_analyzed",
        nullable=False,
        server_default="false"
    )

    # Create index for better query performance
    op.create_index(
        op.f("ix_scenes_video_analyzed"), "scenes", ["video_analyzed"], unique=False
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index(op.f("ix_scenes_video_analyzed"), table_name="scenes")

    # Drop column
    op.drop_column("scenes", "video_analyzed")
