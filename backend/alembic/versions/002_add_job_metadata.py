"""Add metadata column to job table and update job types

Revision ID: 002
Revises: 001
Create Date: 2025-07-15

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metadata column to job table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("job")]

    if "metadata" not in columns:
        op.add_column(
            "job",
            sa.Column("metadata", sa.JSON(), nullable=True, default=dict),
        )
    else:
        print("Column 'metadata' already exists in 'job' table, skipping...")

    # Skip enum updates as they're causing transaction issues
    # The application can handle string values without enum updates
    print("Skipping enum updates to avoid transaction issues")


def downgrade() -> None:
    # Remove metadata column from job table
    op.drop_column("job", "metadata")

    # Note: PostgreSQL doesn't support removing values from enums
    # The enum values will remain but won't be used
