"""add_stash_generate_to_jobtype_enum

Revision ID: a8f27892e503
Revises: 435f474cc89d
Create Date: 2025-07-29 15:40:05.945546

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8f27892e503"
down_revision: Union[str, None] = "435f474cc89d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection to check dialect
    connection = op.get_bind()

    # Only execute for PostgreSQL - SQLite doesn't have enum types
    if connection.dialect.name == "postgresql":
        # Add new enum values for stash_generate job type
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'stash_generate'")
        op.execute(
            "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'STASH_GENERATE'"
        )  # Include uppercase for compatibility


def downgrade() -> None:
    # SQLite doesn't have enum types - nothing to downgrade
    pass
