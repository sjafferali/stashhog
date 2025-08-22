"""add_failed_to_daemon_job_action_enum

Revision ID: 0a18bcf04a9a
Revises: initialize_daemon_status
Create Date: 2025-08-22 02:50:07.215503

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a18bcf04a9a"
down_revision: Union[str, None] = "initialize_daemon_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add FAILED to the daemon_job_action enum type
    # Note: In PostgreSQL, we can't directly alter enum types to add values
    # We need to use a raw SQL command
    # For SQLite, no action is needed as it doesn't enforce enum values

    # Get the dialect name
    from alembic import context

    dialect_name = context.get_context().dialect.name

    if dialect_name == "postgresql":
        op.execute("ALTER TYPE daemonjobaction ADD VALUE IF NOT EXISTS 'FAILED'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum and all dependent columns
    pass
