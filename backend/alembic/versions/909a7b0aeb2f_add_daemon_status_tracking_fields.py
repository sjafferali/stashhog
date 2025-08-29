"""add daemon status tracking fields

Revision ID: 909a7b0aeb2f
Revises: 5735da8d7db7
Create Date: 2025-08-29 10:02:47.329490

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "909a7b0aeb2f"
down_revision: Union[str, None] = "5735da8d7db7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status tracking fields to daemons table
    op.add_column("daemons", sa.Column("current_status", sa.String(500), nullable=True))
    op.add_column("daemons", sa.Column("current_job_id", sa.String(36), nullable=True))
    op.add_column(
        "daemons", sa.Column("current_job_type", sa.String(100), nullable=True)
    )
    op.add_column(
        "daemons",
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Remove the status tracking fields
    op.drop_column("daemons", "status_updated_at")
    op.drop_column("daemons", "current_job_type")
    op.drop_column("daemons", "current_job_id")
    op.drop_column("daemons", "current_status")
