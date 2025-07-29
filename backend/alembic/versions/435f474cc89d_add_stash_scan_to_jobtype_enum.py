"""add_stash_scan_to_jobtype_enum

Revision ID: 435f474cc89d
Revises: e09c4b176d90
Create Date: 2025-07-29 14:29:28.409648

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "435f474cc89d"
down_revision: Union[str, None] = "e09c4b176d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values for stash_scan job type
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'stash_scan'")
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'STASH_SCAN'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
