"""add_auto_video_analysis_daemon

Revision ID: b4b29fa39336
Revises: 19472402cf99
Create Date: 2025-08-12 19:45:04.422839

"""

import uuid
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4b29fa39336"
down_revision: Union[str, None] = "19472402cf99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add auto_video_analysis_daemon to the daemon type enum
    op.execute(
        "ALTER TYPE daemontype ADD VALUE IF NOT EXISTS 'auto_video_analysis_daemon'"
    )

    # Insert daemon record with default configuration
    daemon_id = str(uuid.uuid4())
    op.execute(
        f"""
        INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
        VALUES (
            '{daemon_id}',
            'Auto Video Analysis Daemon',
            'auto_video_analysis_daemon',
            false,
            false,
            'STOPPED',
            '{{"heartbeat_interval": 30, "job_interval_seconds": 600, "batch_size": 50, "auto_approve_plans": true}}'::jsonb,
            NOW(),
            NOW()
        )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    # Remove the daemon record
    op.execute("DELETE FROM daemons WHERE type = 'auto_video_analysis_daemon'")

    # Note: We cannot remove enum values in PostgreSQL, so the enum value remains
