"""add_auto_stash_sync_daemon_record

Revision ID: 114a474c5658
Revises: add11ad951a4
Create Date: 2025-08-13 15:15:55.182902

"""

import uuid
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "114a474c5658"
down_revision: Union[str, None] = "add11ad951a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database dialect
    connection = op.get_bind()
    dialect_name = connection.dialect.name

    # Insert auto stash sync daemon record with appropriate syntax for the database
    daemon_id = str(uuid.uuid4())
    config_json = '{"heartbeat_interval": 30, "job_interval_seconds": 300}'

    if dialect_name == "postgresql":
        op.execute(
            f"""
            INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
            VALUES (
                '{daemon_id}',
                'Auto Stash Sync Daemon',
                'auto_stash_sync_daemon',
                false,
                false,
                'STOPPED',
                '{config_json}'::jsonb,
                NOW(),
                NOW()
            )
            ON CONFLICT (name) DO NOTHING
            """
        )
    else:
        # SQLite and others
        op.execute(
            f"""
            INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
            SELECT
                '{daemon_id}',
                'Auto Stash Sync Daemon',
                'auto_stash_sync_daemon',
                0,
                0,
                'STOPPED',
                '{config_json}',
                datetime('now'),
                datetime('now')
            WHERE NOT EXISTS (
                SELECT 1 FROM daemons WHERE name = 'Auto Stash Sync Daemon'
            )
            """
        )


def downgrade() -> None:
    # Remove auto stash sync daemon record
    op.execute("DELETE FROM daemons WHERE type = 'auto_stash_sync_daemon'")
