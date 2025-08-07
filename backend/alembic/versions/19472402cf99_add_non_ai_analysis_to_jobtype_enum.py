"""add_non_ai_analysis_to_jobtype_enum

Revision ID: 19472402cf99
Revises: 912d68ad6a99
Create Date: 2025-08-07 10:54:50.348695

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19472402cf99"
down_revision: Union[str, None] = "912d68ad6a99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection to check dialect
    connection = op.get_bind()

    # Only execute for PostgreSQL - SQLite doesn't have enum types
    if connection.dialect.name == "postgresql":
        # Add new enum values for non-AI analysis job type
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'non_ai_analysis'")
        # Include uppercase for compatibility
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'NON_AI_ANALYSIS'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
