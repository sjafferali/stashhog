"""add_local_generate_to_jobtype_enum

Revision ID: 743ce2c67347
Revises: add_generated_column_to_scenes
Create Date: 2025-08-19 17:55:31.298835

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "743ce2c67347"
down_revision: Union[str, None] = "add_generated_column_to_scenes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values for local_generate job type
    # Check if we're using PostgreSQL (which has real enums) or SQLite
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'local_generate'")
        op.execute(
            "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'LOCAL_GENERATE'"
        )  # Include uppercase for compatibility
    # For SQLite, enum values are just text, so no migration needed


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    # For SQLite, no action needed
    pass
