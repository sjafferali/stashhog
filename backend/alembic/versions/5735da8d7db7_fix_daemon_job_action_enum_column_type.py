"""fix_daemon_job_action_enum_column_type

Revision ID: 5735da8d7db7
Revises: 0a18bcf04a9a
Create Date: 2025-08-25 18:37:32.162565

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5735da8d7db7"
down_revision: Union[str, None] = "0a18bcf04a9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get the dialect name
    from alembic import context

    dialect_name = context.get_context().dialect.name

    if dialect_name == "postgresql":
        # For PostgreSQL, ensure the enum type exists and update the column type
        connection = op.get_bind()

        # Check if enum type exists
        result = connection.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'daemonjobaction')"
            )
        )
        enum_exists = result.scalar()

        if not enum_exists:
            # Create the enum type
            op.execute(
                "CREATE TYPE daemonjobaction AS ENUM ('LAUNCHED', 'CANCELLED', 'FINISHED', 'FAILED')"
            )

        # Update the column to use the enum type
        # First, temporarily rename the column to avoid conflicts
        op.execute(
            "ALTER TABLE daemon_job_history ALTER COLUMN action TYPE daemonjobaction USING action::daemonjobaction"
        )
    # For SQLite, the String type will work with the SQLAlchemy Enum, no migration needed


def downgrade() -> None:
    # Get the dialect name
    from alembic import context

    dialect_name = context.get_context().dialect.name

    if dialect_name == "postgresql":
        # Revert the column back to VARCHAR(50)
        op.execute(
            "ALTER TABLE daemon_job_history ALTER COLUMN action TYPE VARCHAR(50) USING action::text"
        )
        # Note: We don't drop the enum type as it might be used elsewhere
