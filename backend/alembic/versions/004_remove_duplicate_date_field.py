"""Remove duplicate date field from scene table

Revision ID: 004
Revises: 003
Create Date: 2025-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the duplicate date column
    op.drop_column("scene", "date")


def downgrade() -> None:
    # Re-add the date column
    op.add_column(
        "scene",
        sa.Column("date", sa.String(), nullable=True),
    )
