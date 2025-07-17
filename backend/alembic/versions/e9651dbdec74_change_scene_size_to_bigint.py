"""change_scene_size_to_bigint

Revision ID: e9651dbdec74
Revises: 0e88ad602d07
Create Date: 2025-07-17 13:53:05.118214

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9651dbdec74"
down_revision: Union[str, None] = "0e88ad602d07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change size column from INTEGER to BIGINT to support files larger than 2GB
    op.alter_column(
        "scene",
        "size",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Change size column back to INTEGER
    # Note: This may fail if there are values larger than int32 max
    op.alter_column(
        "scene",
        "size",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
