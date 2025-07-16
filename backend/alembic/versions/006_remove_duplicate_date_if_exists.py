"""Remove duplicate date field from scene table if it exists

Revision ID: 006
Revises: 005
Create Date: 2025-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if the duplicate 'date' column exists
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("scene")]

    if "date" in columns:
        # Drop the duplicate date column
        op.drop_column("scene", "date")


def downgrade() -> None:
    # Check if we need to re-add the date column
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("scene")]

    if "date" not in columns:
        # Re-add the date column as a copy of scene_date
        op.add_column(
            "scene", sa.Column("date", sa.DateTime(timezone=True), nullable=True)
        )
        # Copy scene_date values to date
        op.execute("UPDATE scene SET date = scene_date")
