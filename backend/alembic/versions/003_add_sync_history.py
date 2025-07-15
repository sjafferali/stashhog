"""Add sync_history table

Revision ID: 003
Revises: 002
Create Date: 2025-07-15

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sync_history table
    op.create_table(
        "sync_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("items_synced", sa.Integer(), nullable=False, default=0),
        sa.Column("items_created", sa.Integer(), nullable=False, default=0),
        sa.Column("items_updated", sa.Integer(), nullable=False, default=0),
        sa.Column("items_failed", sa.Integer(), nullable=False, default=0),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(op.f("ix_sync_history_id"), "sync_history", ["id"], unique=False)
    op.create_index(
        op.f("ix_sync_history_entity_type"),
        "sync_history",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sync_history_job_id"), "sync_history", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_sync_history_created_at"), "sync_history", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_sync_history_updated_at"), "sync_history", ["updated_at"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_sync_history_updated_at"), table_name="sync_history")
    op.drop_index(op.f("ix_sync_history_created_at"), table_name="sync_history")
    op.drop_index(op.f("ix_sync_history_job_id"), table_name="sync_history")
    op.drop_index(op.f("ix_sync_history_entity_type"), table_name="sync_history")
    op.drop_index(op.f("ix_sync_history_id"), table_name="sync_history")

    # Drop table
    op.drop_table("sync_history")
