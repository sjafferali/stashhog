"""fix_daemon_datetime_columns_timezone

Revision ID: b0690842a2f6
Revises: 421c8e231cad
Create Date: 2025-08-13 01:39:59.347216

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0690842a2f6"
down_revision: Union[str, None] = "421c8e231cad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database dialect
    connection = op.get_bind()
    dialect_name = connection.dialect.name

    # SQLite doesn't support ALTER COLUMN for type changes
    # and since the tables were just created with timezone-aware columns,
    # we only need to run this for PostgreSQL databases
    if dialect_name != "postgresql":
        return

    # Change datetime columns to be timezone-aware in daemons table
    op.alter_column(
        "daemons",
        "started_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    op.alter_column(
        "daemons",
        "last_heartbeat",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    op.alter_column(
        "daemons",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    op.alter_column(
        "daemons",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    # Change datetime columns in daemon_logs table
    op.alter_column(
        "daemon_logs",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    # Change datetime columns in daemon_job_history table
    op.alter_column(
        "daemon_job_history",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Get database dialect
    connection = op.get_bind()
    dialect_name = connection.dialect.name

    # Skip for non-PostgreSQL databases
    if dialect_name != "postgresql":
        return

    # Revert to timezone-naive datetime columns in daemons table
    op.alter_column(
        "daemons",
        "started_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    op.alter_column(
        "daemons",
        "last_heartbeat",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    op.alter_column(
        "daemons",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    op.alter_column(
        "daemons",
        "updated_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    # Revert daemon_logs table
    op.alter_column(
        "daemon_logs",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    # Revert daemon_job_history table
    op.alter_column(
        "daemon_job_history",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
