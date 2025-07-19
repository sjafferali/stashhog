"""fix_jobtype_enum_values

Revision ID: 627297927ae1
Revises: 32d96105b4a5
Create Date: 2025-07-18 18:37:45.908086

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "627297927ae1"
down_revision: Union[str, None] = "32d96105b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing lowercase enum values
    # These use IF NOT EXISTS to avoid errors if they already exist
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'analysis'")
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'apply_plan'")
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'export'")
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'import'")
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'cleanup'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
