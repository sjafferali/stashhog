"""convert_uppercase_enum_values_to_lowercase

Revision ID: 4caf6db6de5b
Revises: 06a1610596d5
Create Date: 2025-07-18 19:39:45.699109

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4caf6db6de5b"
down_revision: Union[str, None] = "06a1610596d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert all uppercase enum values to lowercase in the job table

    # Update job type values
    op.execute("UPDATE job SET type = 'sync' WHERE type = 'SYNC'")
    op.execute("UPDATE job SET type = 'sync_all' WHERE type = 'SYNC_ALL'")
    op.execute("UPDATE job SET type = 'sync_scenes' WHERE type = 'SYNC_SCENES'")
    op.execute("UPDATE job SET type = 'sync_performers' WHERE type = 'SYNC_PERFORMERS'")
    op.execute("UPDATE job SET type = 'sync_tags' WHERE type = 'SYNC_TAGS'")
    op.execute("UPDATE job SET type = 'sync_studios' WHERE type = 'SYNC_STUDIOS'")
    op.execute("UPDATE job SET type = 'analysis' WHERE type = 'ANALYSIS'")
    op.execute("UPDATE job SET type = 'apply_plan' WHERE type = 'APPLY_PLAN'")
    op.execute(
        "UPDATE job SET type = 'generate_details' WHERE type = 'GENERATE_DETAILS'"
    )
    op.execute("UPDATE job SET type = 'export' WHERE type = 'EXPORT'")
    op.execute("UPDATE job SET type = 'import' WHERE type = 'IMPORT'")
    op.execute("UPDATE job SET type = 'cleanup' WHERE type = 'CLEANUP'")

    # Update job status values
    op.execute("UPDATE job SET status = 'pending' WHERE status = 'PENDING'")
    op.execute("UPDATE job SET status = 'running' WHERE status = 'RUNNING'")
    op.execute("UPDATE job SET status = 'completed' WHERE status = 'COMPLETED'")
    op.execute("UPDATE job SET status = 'failed' WHERE status = 'FAILED'")
    op.execute("UPDATE job SET status = 'cancelled' WHERE status = 'CANCELLED'")


def downgrade() -> None:
    # Convert lowercase values back to uppercase

    # Update job type values
    op.execute("UPDATE job SET type = 'SYNC' WHERE type = 'sync'")
    op.execute("UPDATE job SET type = 'SYNC_ALL' WHERE type = 'sync_all'")
    op.execute("UPDATE job SET type = 'SYNC_SCENES' WHERE type = 'sync_scenes'")
    op.execute("UPDATE job SET type = 'SYNC_PERFORMERS' WHERE type = 'sync_performers'")
    op.execute("UPDATE job SET type = 'SYNC_TAGS' WHERE type = 'sync_tags'")
    op.execute("UPDATE job SET type = 'SYNC_STUDIOS' WHERE type = 'sync_studios'")
    op.execute("UPDATE job SET type = 'ANALYSIS' WHERE type = 'analysis'")
    op.execute("UPDATE job SET type = 'APPLY_PLAN' WHERE type = 'apply_plan'")
    op.execute(
        "UPDATE job SET type = 'GENERATE_DETAILS' WHERE type = 'generate_details'"
    )
    op.execute("UPDATE job SET type = 'EXPORT' WHERE type = 'export'")
    op.execute("UPDATE job SET type = 'IMPORT' WHERE type = 'import'")
    op.execute("UPDATE job SET type = 'CLEANUP' WHERE type = 'cleanup'")
    op.execute(
        "UPDATE job SET type = 'VIDEO_TAG_ANALYSIS' WHERE type = 'video_tag_analysis'"
    )

    # Update job status values
    op.execute("UPDATE job SET status = 'PENDING' WHERE status = 'pending'")
    op.execute("UPDATE job SET status = 'RUNNING' WHERE status = 'running'")
    op.execute("UPDATE job SET status = 'COMPLETED' WHERE status = 'completed'")
    op.execute("UPDATE job SET status = 'FAILED' WHERE status = 'failed'")
    op.execute("UPDATE job SET status = 'CANCELLED' WHERE status = 'cancelled'")
