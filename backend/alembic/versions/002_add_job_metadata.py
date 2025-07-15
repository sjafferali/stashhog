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
    # Add metadata column to job table
    op.add_column(
        "job",
        sa.Column("metadata", sa.JSON(), nullable=True, default=dict),
    )

    # Update JobType enum to include new values
    # First, alter the enum type to add new values
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'sync'")
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'sync_all'")
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'sync_scenes'")
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'sync_performers'")
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'sync_tags'")
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'sync_studios'")
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'generate_details'")


def downgrade() -> None:
    # Remove metadata column from job table
    op.drop_column("job", "metadata")

    # Note: PostgreSQL doesn't support removing values from enums
    # The enum values will remain but won't be used
