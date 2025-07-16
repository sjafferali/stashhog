"""Add rejected column to plan_change table

Revision ID: 007
Revises: 006
Create Date: 2025-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the rejected column to plan_change table
    op.add_column(
        "plan_change",
        sa.Column("rejected", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Create index on rejected column
    op.create_index(
        op.f("ix_plan_change_rejected"), "plan_change", ["rejected"], unique=False
    )


def downgrade() -> None:
    # Drop index on rejected column
    op.drop_index(op.f("ix_plan_change_rejected"), table_name="plan_change")
    # Drop the rejected column
    op.drop_column("plan_change", "rejected")
