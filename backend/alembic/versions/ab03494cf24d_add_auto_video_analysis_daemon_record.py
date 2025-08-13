"""add_auto_video_analysis_daemon_record

Revision ID: ab03494cf24d
Revises: 19472402cf99
Create Date: 2025-08-12 20:12:03.326698

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab03494cf24d"
down_revision: Union[str, None] = "19472402cf99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database dialect
    connection = op.get_bind()
    dialect_name = connection.dialect.name

    # Insert auto video analysis daemon record
    daemon_id = str(uuid.uuid4())
    config_json = '{"heartbeat_interval": 30, "job_interval_seconds": 600, "batch_size": 50, "auto_approve_plans": true}'

    if dialect_name == "postgresql":
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
                '{config_json}'::jsonb,
                NOW(),
                NOW()
            )
            ON CONFLICT (name) DO NOTHING
            """
        )
    else:
        # SQLite doesn't support ON CONFLICT directly, so check first
        result = connection.execute(
            sa.text("SELECT id FROM daemons WHERE name = :name"),
            {"name": "Auto Video Analysis Daemon"},
        )
        if not result.fetchone():
            op.execute(
                f"""
                INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
                VALUES (
                    '{daemon_id}',
                    'Auto Video Analysis Daemon',
                    'auto_video_analysis_daemon',
                    0,
                    0,
                    'STOPPED',
                    '{config_json}',
                    datetime('now'),
                    datetime('now')
                )
                """
            )


def downgrade() -> None:
    # Remove the daemon record
    op.execute("DELETE FROM daemons WHERE type = 'auto_video_analysis_daemon'")
