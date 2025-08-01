"""add_test_to_jobtype_enum

Revision ID: 912d68ad6a99
Revises: d3a21e0e6edd
Create Date: 2025-08-01 16:00:29.476106

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "912d68ad6a99"
down_revision: Union[str, None] = "d3a21e0e6edd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection to check dialect
    connection = op.get_bind()

    # Only execute for PostgreSQL - SQLite doesn't have enum types
    if connection.dialect.name == "postgresql":
        # Add new enum values for test job type
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'test'")
        op.execute(
            "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'TEST'"
        )  # Include uppercase for compatibility


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
