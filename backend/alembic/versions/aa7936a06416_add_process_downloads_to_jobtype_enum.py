"""add_process_downloads_to_jobtype_enum

Revision ID: aa7936a06416
Revises: 2518f0af4f66
Create Date: 2025-07-28 23:51:18.428271

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa7936a06416"
down_revision: Union[str, None] = "2518f0af4f66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values for process_downloads job type
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'process_downloads'")
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'PROCESS_DOWNLOADS'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
