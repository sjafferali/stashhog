"""add_lowercase_jobstatus_enum_values

Revision ID: 06a1610596d5
Revises: 627297927ae1
Create Date: 2025-07-18 19:01:00.140826

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06a1610596d5"
down_revision: Union[str, None] = "627297927ae1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lowercase jobstatus enum values
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'running'")
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'completed'")
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'failed'")
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
