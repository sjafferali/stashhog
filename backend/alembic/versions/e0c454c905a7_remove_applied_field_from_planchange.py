"""Remove applied field from PlanChange

Revision ID: e0c454c905a7
Revises: e5da50fb8835
Create Date: 2025-08-13 19:18:11.462275

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e0c454c905a7"
down_revision: Union[str, None] = "e5da50fb8835"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update any records where applied=True to have status='applied'
    # This ensures no data loss during migration
    op.execute(
        """
        UPDATE plan_change
        SET status = 'applied'
        WHERE applied = TRUE AND status IN ('pending', 'approved')
        """
    )

    # Drop the indexes first (if they exist)
    try:
        op.drop_index("ix_plan_change_applied", table_name="plan_change")
    except Exception:
        pass  # Index might not exist

    try:
        op.drop_index("idx_change_applied_plan", table_name="plan_change")
    except Exception:
        pass  # Index might not exist

    # Drop the column
    op.drop_column("plan_change", "applied")


def downgrade() -> None:
    # Add the column back
    op.add_column(
        "plan_change",
        sa.Column("applied", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Recreate the indexes
    op.create_index("ix_plan_change_applied", "plan_change", ["applied"])
    op.create_index("idx_change_applied_plan", "plan_change", ["applied", "plan_id"])

    # Restore data based on status field
    op.execute(
        """
        UPDATE plan_change
        SET applied = TRUE
        WHERE status = 'applied'
        """
    )
