"""add test daemon record

Revision ID: d3a21e0e6edd
Revises: a8bae0a82f5f
Create Date: 2025-08-01 11:06:04.710090

"""

import uuid
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3a21e0e6edd"
down_revision: Union[str, None] = "a8bae0a82f5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert test daemon record
    op.execute(
        f"""
        INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
        VALUES (
            '{uuid.uuid4()}',
            'Test Daemon',
            'test_daemon',
            false,
            false,
            'STOPPED',
            '{{"log_interval": 5, "job_interval": 30, "heartbeat_interval": 10, "simulate_errors": false}}'::jsonb,
            NOW(),
            NOW()
        )
        """
    )


def downgrade() -> None:
    # Remove test daemon record
    op.execute("DELETE FROM daemons WHERE type = 'test_daemon'")
