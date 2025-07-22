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
down_revision: Union[str, None] = "fb84ffeb960e"
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

    # Update PlanStatus enum: rename 'applied' to 'complete'
    # First, add the new value
    op.execute("ALTER TYPE planstatus ADD VALUE 'complete'")

    # Update existing records
    op.execute("UPDATE analysis_plan SET status = 'complete' WHERE status = 'applied'")

    # Note: We can't remove 'applied' from the enum in PostgreSQL without recreating it
    # The old value will remain but won't be used

    # Update the index name to reflect the new status
    op.drop_index("idx_plan_status_applied", table_name="analysis_plan")
    op.create_index(
        "idx_plan_status_complete", "analysis_plan", ["status", "applied_at"]
    )


def downgrade() -> None:
    # Revert index name
    op.drop_index("idx_plan_status_complete", table_name="analysis_plan")
    op.create_index(
        "idx_plan_status_applied", "analysis_plan", ["status", "applied_at"]
    )

    # Update records back to 'applied' from 'complete'
    op.execute("UPDATE analysis_plan SET status = 'applied' WHERE status = 'complete'")

    # Note: We can't remove 'complete' from the enum without recreating it

    # Drop the status column index
    op.drop_index("idx_change_status_plan", table_name="plan_change")

    # Drop the status column
    op.drop_column("plan_change", "status")

    # Drop the changestatus enum
    changestatus_enum = sa.Enum(
        "pending", "approved", "rejected", "applied", name="changestatus"
    )
    changestatus_enum.drop(op.get_bind())
