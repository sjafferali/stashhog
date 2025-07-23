"""add sync_log table

Revision ID: a875b5703002
Revises: 721bff50805b
Create Date: 2025-07-22 20:45:03.163516

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a875b5703002"
down_revision: Union[str, None] = "721bff50805b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sync_log table
    op.create_table(
        "sync_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sync_history_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("sync_type", sa.String(), nullable=False),
        sa.Column("had_changes", sa.Boolean(), nullable=True),
        sa.Column("change_type", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["sync_history_id"],
            ["sync_history.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_sync_log_entity_id", "sync_log", ["entity_id"], unique=False)
    op.create_index(
        "idx_sync_log_sync_history_id", "sync_log", ["sync_history_id"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_sync_log_sync_history_id", table_name="sync_log")
    op.drop_index("idx_sync_log_entity_id", table_name="sync_log")

    # Drop table
    op.drop_table("sync_log")
