"""remove deprecated file columns from scene table

Revision ID: c570659854a3
Revises: fb84ffeb960e
Create Date: 2025-07-21 22:56:30.383620

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c570659854a3"
down_revision: Union[str, None] = "fb84ffeb960e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove deprecated file-related columns from scene table
    # These columns have been migrated to the scene_file table
    op.drop_column("scene", "file_path")
    op.drop_column("scene", "paths")
    op.drop_column("scene", "duration")
    op.drop_column("scene", "size")
    op.drop_column("scene", "height")
    op.drop_column("scene", "width")
    op.drop_column("scene", "framerate")
    op.drop_column("scene", "bitrate")
    op.drop_column("scene", "codec")


def downgrade() -> None:
    # Re-add columns for rollback
    op.add_column("scene", sa.Column("file_path", sa.String(), nullable=True))
    op.add_column(
        "scene", sa.Column("paths", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column("scene", sa.Column("duration", sa.Float(), nullable=True))
    op.add_column("scene", sa.Column("size", sa.BigInteger(), nullable=True))
    op.add_column("scene", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("scene", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("scene", sa.Column("framerate", sa.Float(), nullable=True))
    op.add_column("scene", sa.Column("bitrate", sa.Integer(), nullable=True))
    op.add_column("scene", sa.Column("codec", sa.String(), nullable=True))
