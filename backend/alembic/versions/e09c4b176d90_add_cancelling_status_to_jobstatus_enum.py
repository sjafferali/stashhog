"""add_cancelling_status_to_jobstatus_enum

Revision ID: e09c4b176d90
Revises: aa7936a06416
Create Date: 2025-07-29 08:17:38.347152

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e09c4b176d90"
down_revision: Union[str, None] = "aa7936a06416"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cancelling status to jobstatus enum
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'cancelling'")
    op.execute(
        "ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'CANCELLING'"
    )  # Add uppercase for compatibility


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
