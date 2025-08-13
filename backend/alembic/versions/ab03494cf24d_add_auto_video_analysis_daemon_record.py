"""add_auto_video_analysis_daemon_record

Revision ID: ab03494cf24d
Revises: 19472402cf99
Create Date: 2025-08-12 20:12:03.326698

"""

import uuid
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab03494cf24d"
down_revision: Union[str, None] = "19472402cf99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert auto video analysis daemon record
    # Note: daemons.type is a String column, not an enum
    op.execute(
        f"""
        INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
        VALUES (
            '{uuid.uuid4()}',
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
