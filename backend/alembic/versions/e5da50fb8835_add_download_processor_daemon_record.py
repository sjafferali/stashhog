"""Add download processor daemon record

Revision ID: e5da50fb8835
Revises: 9be89d104d06
Create Date: 2025-08-13 18:38:50.543318

"""

import uuid
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5da50fb8835"
down_revision: Union[str, None] = "9be89d104d06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert download processor daemon record
    # Note: daemons.type is a String column, not an enum
    op.execute(
        f"""
        INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
        VALUES (
            '{uuid.uuid4()}',
            'Download Processor Daemon',
            'download_processor_daemon',
            false,
            false,
            'STOPPED',
            '{{"heartbeat_interval": 30, "job_interval_seconds": 300}}',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM daemons WHERE type = 'download_processor_daemon'")
