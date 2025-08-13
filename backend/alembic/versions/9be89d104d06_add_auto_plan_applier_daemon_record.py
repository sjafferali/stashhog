"""add_auto_plan_applier_daemon_record

Revision ID: 9be89d104d06
Revises: b0690842a2f6
Create Date: 2025-08-13 10:12:29.758763

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9be89d104d06"
down_revision: Union[str, None] = "b0690842a2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database dialect
    connection = op.get_bind()
    dialect_name = connection.dialect.name

    # Insert auto plan applier daemon record
    daemon_id = str(uuid.uuid4())
    config_json = '{"heartbeat_interval": 30, "job_interval_seconds": 60, "plan_prefix_filter": [], "auto_approve_all_changes": false}'

    if dialect_name == "postgresql":
        op.execute(
            f"""
            INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
            VALUES (
                '{daemon_id}',
                'Auto Plan Applier Daemon',
                'auto_plan_applier_daemon',
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
            {"name": "Auto Plan Applier Daemon"},
        )
        if not result.fetchone():
            op.execute(
                f"""
                INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration, created_at, updated_at)
                VALUES (
                    '{daemon_id}',
                    'Auto Plan Applier Daemon',
                    'auto_plan_applier_daemon',
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
    op.execute("DELETE FROM daemons WHERE type = 'auto_plan_applier_daemon'")
