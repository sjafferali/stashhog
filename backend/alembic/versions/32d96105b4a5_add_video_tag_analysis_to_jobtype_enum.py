"""add_video_tag_analysis_to_jobtype_enum

Revision ID: 32d96105b4a5
Revises: e9651dbdec74
Create Date: 2025-07-18 18:26:18.922005

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "32d96105b4a5"
down_revision: Union[str, None] = "e9651dbdec74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add VIDEO_TAG_ANALYSIS to the jobtype enum
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'video_tag_analysis'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass
