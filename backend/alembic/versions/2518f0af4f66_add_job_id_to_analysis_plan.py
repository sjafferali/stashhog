"""add_job_id_to_analysis_plan

Revision ID: 2518f0af4f66
Revises: a875b5703002
Create Date: 2025-07-22 22:20:46.330698

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2518f0af4f66"
down_revision: Union[str, None] = "a875b5703002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add job_id column to analysis_plans table
    op.add_column("analysis_plans", sa.Column("job_id", sa.String(), nullable=True))

    # Create index on job_id for faster lookups
    op.create_index(
        op.f("ix_analysis_plans_job_id"), "analysis_plans", ["job_id"], unique=False
    )

    # Add PENDING to the PlanStatus enum if it doesn't exist
    op.execute("ALTER TYPE planstatus ADD VALUE IF NOT EXISTS 'PENDING'")


def downgrade() -> None:
    # Remove index
    op.drop_index(op.f("ix_analysis_plans_job_id"), table_name="analysis_plans")

    # Remove job_id column
    op.drop_column("analysis_plans", "job_id")

    # Note: We cannot remove the PENDING value from the enum in PostgreSQL
    # This would require recreating the entire enum type
