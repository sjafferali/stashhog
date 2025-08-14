"""Add auto stash generation daemon record

Revision ID: 10705e2245ad
Revises: e0c454c905a7
Create Date: 2025-08-14 13:15:02.604510

"""

import uuid
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10705e2245ad"
down_revision: Union[str, None] = "e0c454c905a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert auto stash generation daemon record
    # Note: daemons.type is a String column, not an enum
    op.execute(
        f"""
        INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
        VALUES (
            '{uuid.uuid4()}',
            'Auto Stash Generation Daemon',
            'auto_stash_generation_daemon',
            false,
            false,
            'STOPPED',
            '{{"heartbeat_interval": 30, "job_interval_seconds": 3600, "retry_interval_seconds": 3600}}',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM daemons WHERE type = 'auto_stash_generation_daemon'")
