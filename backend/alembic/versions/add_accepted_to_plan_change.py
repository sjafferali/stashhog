"""Add accepted column to plan_change table

Revision ID: add_accepted_column
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_accepted_column"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add accepted column to plan_change table
    op.add_column(
        "plan_change",
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create index on accepted column for better query performance
    op.create_index("ix_plan_change_accepted", "plan_change", ["accepted"])


def downgrade() -> None:
    # Remove index
    op.drop_index("ix_plan_change_accepted", table_name="plan_change")

    # Remove column
    op.drop_column("plan_change", "accepted")
