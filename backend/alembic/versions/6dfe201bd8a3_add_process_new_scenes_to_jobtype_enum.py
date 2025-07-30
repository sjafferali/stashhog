"""add_process_new_scenes_to_jobtype_enum

Revision ID: 6dfe201bd8a3
Revises: fc61222b7dc6
Create Date: 2025-07-29 22:15:40.084480

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6dfe201bd8a3"
down_revision: Union[str, None] = "fc61222b7dc6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values for process_new_scenes job type
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'process_new_scenes'")
    op.execute(
        "ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'PROCESS_NEW_SCENES'"
    )  # Include uppercase for compatibility


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
