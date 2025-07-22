"""add status field to plan_change and update plan status enum

Revision ID: 9f53995644a3
Revises: fb84ffeb960e
Create Date: 2025-07-21 22:34:20.025414

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f53995644a3"
down_revision: Union[str, None] = "c570659854a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the new changestatus enum
    changestatus_enum = sa.Enum(
        "pending", "approved", "rejected", "applied", name="changestatus"
    )
    changestatus_enum.create(op.get_bind())

    # Add the status column to plan_change table with default 'pending'
    op.add_column(
        "plan_change",
        sa.Column(
            "status", changestatus_enum, nullable=False, server_default="pending"
        ),
    )

    # Create an index on the new status column
    op.create_index("idx_change_status_plan", "plan_change", ["status", "plan_id"])

    # Migrate existing data from boolean fields to the new status field
    # This uses raw SQL to handle the conditional logic
    op.execute(
        """
        UPDATE plan_change
        SET status = CASE
            WHEN applied = true THEN 'applied'::changestatus
            WHEN rejected = true THEN 'rejected'::changestatus
            WHEN accepted = true THEN 'approved'::changestatus
            ELSE 'pending'::changestatus
        END
    """
    )

    # No changes needed to PlanStatus enum - keeping APPLIED as is


def downgrade() -> None:
    # No changes to revert for PlanStatus enum since we didn't modify it

    # Drop the status column index
    op.drop_index("idx_change_status_plan", table_name="plan_change")

    # Drop the status column
    op.drop_column("plan_change", "status")

    # Drop the changestatus enum
    changestatus_enum = sa.Enum(
        "pending", "approved", "rejected", "applied", name="changestatus"
    )
    changestatus_enum.drop(op.get_bind())
