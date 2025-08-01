"""add daemons tables

Revision ID: a8bae0a82f5f
Revises: 923456ab3699
Create Date: 2025-08-01 10:52:13.849686

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8bae0a82f5f"
down_revision: Union[str, None] = "923456ab3699"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create daemons table
    op.create_table(
        "daemons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("auto_start", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create indexes
    op.create_index("ix_daemons_type", "daemons", ["type"])
    op.create_index("ix_daemons_status", "daemons", ["status"])
    op.create_index("ix_daemons_enabled", "daemons", ["enabled"])

    # Create daemon_logs table
    op.create_table(
        "daemon_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for logs
    op.create_index("ix_daemon_logs_daemon_id", "daemon_logs", ["daemon_id"])
    op.create_index("ix_daemon_logs_created_at", "daemon_logs", ["created_at"])
    op.create_index("ix_daemon_logs_level", "daemon_logs", ["level"])

    # Create daemon_job_history table
    op.create_table(
        "daemon_job_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for job history
    op.create_index(
        "ix_daemon_job_history_daemon_id", "daemon_job_history", ["daemon_id"]
    )
    op.create_index("ix_daemon_job_history_job_id", "daemon_job_history", ["job_id"])
    op.create_index(
        "ix_daemon_job_history_created_at", "daemon_job_history", ["created_at"]
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("daemon_job_history")
    op.drop_table("daemon_logs")
    op.drop_table("daemons")
