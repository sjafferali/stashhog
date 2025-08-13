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
    # Get database connection to check dialect
    connection = op.get_bind()

    if connection.dialect.name == "postgresql":
        # PostgreSQL version with JSONB operations
        # Update existing jobs with removed types to sync type
        op.execute(
            """
            UPDATE job
            SET type = 'sync',
                metadata = CASE
                    WHEN metadata IS NULL THEN json_build_object('migrated_from', type)::json
                    ELSE (metadata::jsonb || json_build_object('migrated_from', type)::jsonb)::json
                END
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
            SET metadata = (
                SELECT json_object_agg(
                    CASE WHEN key = 'force' THEN 'full_resync' ELSE key END,
                    value
                )::json
                FROM json_each(metadata)
            )
            WHERE type = 'sync'
            AND metadata IS NOT NULL
            AND metadata::jsonb ? 'force'
        """
        )

        # Remove 'force' parameter from sync_scenes jobs
        op.execute(
            """
            UPDATE job
            SET metadata = (
                SELECT json_object_agg(key, value)::json
                FROM json_each(metadata)
                WHERE key != 'force'
            )
            WHERE type = 'sync_scenes'
            AND metadata IS NOT NULL
            AND metadata::jsonb ? 'force'
        """
        )
    else:
        # SQLite version - simpler JSON operations
        # Update existing jobs with removed types to sync type
        op.execute(
            """
            UPDATE job
            SET type = 'sync'
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


def downgrade() -> None:
    # This migration is not easily reversible as we're removing enum values
    # and consolidating job types. The migrated_from field in metadata
    # preserves the original type if restoration is needed.
    pass
