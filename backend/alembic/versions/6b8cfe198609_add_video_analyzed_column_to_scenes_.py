"""Add video_analyzed column to scene table

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
    # Add video_analyzed column to scene table
    # First add as nullable to avoid long table rewrite
    op.add_column(
        "scene",
        sa.Column("video_analyzed", sa.Boolean(), nullable=True),
    )

    # Set default value for existing rows in smaller batches to avoid timeout
    connection = op.get_bind()
    batch_size = 10000
    offset = 0

    while True:
        result = connection.execute(
            sa.text(
                f"""
                UPDATE scene
                SET video_analyzed = false
                WHERE video_analyzed IS NULL
                AND id IN (
                    SELECT id FROM scene
                    WHERE video_analyzed IS NULL
                    ORDER BY id
                    LIMIT {batch_size}
                )
            """
            )
        )

        if result.rowcount == 0:
            break

        offset += batch_size
        # Small delay to prevent overwhelming the database
        connection.execute(sa.text("SELECT pg_sleep(0.1)"))

    # Now make it NOT NULL with default
    op.alter_column("scene", "video_analyzed", nullable=False, server_default="false")

    # Create index for better query performance
    op.create_index(
        op.f("ix_scene_video_analyzed"), "scene", ["video_analyzed"], unique=False
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index(op.f("ix_scene_video_analyzed"), table_name="scene")

    # Drop column
    op.drop_column("scene", "video_analyzed")
