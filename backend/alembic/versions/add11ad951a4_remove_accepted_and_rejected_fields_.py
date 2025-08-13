"""Remove accepted and rejected fields from PlanChange

Revision ID: add11ad951a4
Revises: 9be89d104d06
Create Date: 2025-08-13 12:39:49.069956

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add11ad951a4"
down_revision: Union[str, None] = "9be89d104d06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, update any existing data to ensure status field is set correctly
    # Set status to APPROVED for any records where accepted=True
    op.execute(
        """
        UPDATE plan_change
        SET status = 'approved'
        WHERE accepted = TRUE AND status = 'pending'
    """
    )

    # Set status to REJECTED for any records where rejected=True
    op.execute(
        """
        UPDATE plan_change
        SET status = 'rejected'
        WHERE rejected = TRUE AND status = 'pending'
    """
    )

    # Set status to APPLIED for any records where applied=True
    op.execute(
        """
        UPDATE plan_change
        SET status = 'applied'
        WHERE applied = TRUE AND status IN ('pending', 'approved')
    """
    )

    # Drop the indexes first
    op.drop_index("ix_plan_change_accepted", table_name="plan_change")
    op.drop_index("ix_plan_change_rejected", table_name="plan_change")

    # Drop the columns
    op.drop_column("plan_change", "accepted")
    op.drop_column("plan_change", "rejected")


def downgrade() -> None:
    # Add the columns back
    op.add_column(
        "plan_change",
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "plan_change",
        sa.Column("rejected", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Recreate the indexes
    op.create_index("ix_plan_change_accepted", "plan_change", ["accepted"])
    op.create_index("ix_plan_change_rejected", "plan_change", ["rejected"])

    # Restore data based on status field
    op.execute(
        """
        UPDATE plan_change
        SET accepted = TRUE
        WHERE status IN ('approved', 'applied')
    """
    )

    op.execute(
        """
        UPDATE plan_change
        SET rejected = TRUE
        WHERE status = 'rejected'
    """
    )
