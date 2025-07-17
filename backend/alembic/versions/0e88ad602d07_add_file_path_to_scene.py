"""add_file_path_to_scene

Revision ID: 0e88ad602d07
Revises: 008
Create Date: 2025-07-16 23:07:23.694768

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0e88ad602d07"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add file_path column to scene table
    op.add_column("scene", sa.Column("file_path", sa.String(), nullable=True))


def downgrade() -> None:
    # Remove file_path column from scene table
    op.drop_column("scene", "file_path")
