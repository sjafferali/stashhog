"""add_remove_orphaned_entities_to_jobtype_enum

Revision ID: 421c8e231cad
Revises: 423d516aebb3
Create Date: 2025-08-12 21:10:27.255840

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "421c8e231cad"
down_revision: Union[str, None] = "423d516aebb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection to check dialect
    connection = op.get_bind()

    # Only execute for PostgreSQL - SQLite doesn't have enum types
    if connection.dialect.name == "postgresql":
        # Add new enum values for remove_orphaned_entities job type
        op.execute(
            "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'remove_orphaned_entities'"
        )
        op.execute(
            "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'REMOVE_ORPHANED_ENTITIES'"
        )


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
