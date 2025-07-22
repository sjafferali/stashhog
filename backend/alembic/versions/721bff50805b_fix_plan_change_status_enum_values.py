"""fix plan change status enum values

Revision ID: 721bff50805b
Revises: 9f53995644a3
Create Date: 2025-07-22 16:54:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "721bff50805b"
down_revision: Union[str, None] = "9f53995644a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix any existing records that have plain string values instead of enum values
    # This ensures all status values are properly cast to the changestatus enum type
    op.execute(
        """
        UPDATE plan_change
        SET status = status::text::changestatus
        WHERE status IS NOT NULL
        """
    )

    # Update the default constraint to use proper enum casting
    # First drop the existing column default
    op.alter_column(
        "plan_change",
        "status",
        server_default=None,
        existing_type=sa.Enum(
            "pending", "approved", "rejected", "applied", name="changestatus"
        ),
        existing_nullable=False,
    )

    # Then add the new default with proper enum casting
    op.alter_column(
        "plan_change",
        "status",
        server_default=sa.text("'pending'::changestatus"),
        existing_type=sa.Enum(
            "pending", "approved", "rejected", "applied", name="changestatus"
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revert to the original default
    op.alter_column(
        "plan_change",
        "status",
        server_default="pending",
        existing_type=sa.Enum(
            "pending", "approved", "rejected", "applied", name="changestatus"
        ),
        existing_nullable=False,
    )
