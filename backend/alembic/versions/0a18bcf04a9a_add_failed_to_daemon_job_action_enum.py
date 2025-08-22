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
    # Note: The action column was created as a simple String(50) in the original migration,
    # not as an enum type. So for PostgreSQL, we first need to check if the enum exists,
    # and if not, create it and update the column type.
    # For SQLite, no action is needed as it doesn't enforce enum values

    # Get the dialect name
    import sqlalchemy as sa

    from alembic import context

    dialect_name = context.get_context().dialect.name

    if dialect_name == "postgresql":
        # Check if enum type exists
        connection = op.get_bind()
        result = connection.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'daemonjobaction')"
            )
        )
        enum_exists = result.scalar()

        if enum_exists:
            # Enum exists, just add the new value
            op.execute("ALTER TYPE daemonjobaction ADD VALUE IF NOT EXISTS 'FAILED'")
        else:
            # Enum doesn't exist, create it with all values
            # Create the enum type
            op.execute(
                "CREATE TYPE daemonjobaction AS ENUM ('LAUNCHED', 'CANCELLED', 'FINISHED', 'FAILED')"
            )
            # Update the column to use the enum
            op.execute(
                "ALTER TABLE daemon_job_history ALTER COLUMN action TYPE daemonjobaction USING action::daemonjobaction"
            )


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum and all dependent columns
    pass
