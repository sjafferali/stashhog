"""add_check_stash_generate_to_jobtype_enum

Revision ID: fc61222b7dc6
Revises: a8f27892e503
Create Date: 2025-07-29 15:55:51.974742

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fc61222b7dc6"
down_revision: Union[str, None] = "a8f27892e503"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values for check_stash_generate job type
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'check_stash_generate'")
    op.execute(
        "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'CHECK_STASH_GENERATE'"
    )  # Include uppercase for compatibility


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
