"""remove individual sync job types

Revision ID: 7c11b1a6bde7
Revises: 6dfe201bd8a3
Create Date: 2025-07-31 12:06:23.871978

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c11b1a6bde7"
down_revision: Union[str, None] = "6dfe201bd8a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update existing jobs with removed types to sync type
    # Note: We're updating both lowercase and uppercase versions to handle any legacy data
    op.execute(
        """
        UPDATE job
        SET type = 'sync',
            job_metadata = jsonb_set(
                COALESCE(job_metadata, '{}'),
                '{migrated_from}',
                to_jsonb(type)
            )
        WHERE type IN ('sync_performers', 'sync_tags', 'sync_studios', 'SYNC_PERFORMERS', 'SYNC_TAGS', 'SYNC_STUDIOS')
    """
    )

    # Update sync_all to sync
    op.execute(
        """
        UPDATE job
        SET type = 'sync'
        WHERE type IN ('sync_all', 'SYNC_ALL')
    """
    )

    # Update job metadata for 'force' parameter to 'full_resync'
    op.execute(
        """
        UPDATE job
        SET job_metadata = jsonb_set(
            job_metadata - 'force',
            '{full_resync}',
            COALESCE(job_metadata->>'force', 'false')::jsonb
        )
        WHERE type = 'sync' AND job_metadata ? 'force'
    """
    )

    # Remove 'force' parameter from sync_scenes jobs
    op.execute(
        """
        UPDATE job
        SET job_metadata = job_metadata - 'force'
        WHERE type = 'sync_scenes' AND job_metadata ? 'force'
    """
    )


def downgrade() -> None:
    # This migration is not easily reversible as we're removing enum values
    # and consolidating job types. The migrated_from field in metadata
    # preserves the original type if restoration is needed.
    pass
