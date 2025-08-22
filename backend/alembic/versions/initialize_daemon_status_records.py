"""initialize_daemon_status_records

Revision ID: initialize_daemon_status
Revises: 50fefb17d3ad
Create Date: 2025-08-21 17:35:00.000000

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "initialize_daemon_status"
down_revision: Union[str, None] = "50fefb17d3ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create daemon_status records for all existing daemons."""
    # Get connection
    conn = op.get_bind()

    # Get all daemons
    result = conn.execute(sa.text("SELECT id FROM daemons"))
    daemon_ids = [row[0] for row in result]

    # Create daemon_status record for each daemon if it doesn't exist
    for daemon_id in daemon_ids:
        # Check if status record already exists
        existing = conn.execute(
            sa.text("SELECT id FROM daemon_status WHERE daemon_id = :daemon_id"),
            {"daemon_id": daemon_id},
        ).first()

        if not existing:
            # Create new status record
            conn.execute(
                sa.text(
                    """
                    INSERT INTO daemon_status (
                        id, daemon_id, current_activity, current_progress,
                        items_processed, items_pending, last_error_message,
                        last_error_time, error_count_24h, warning_count_24h,
                        jobs_launched_24h, jobs_completed_24h, jobs_failed_24h,
                        health_score, avg_job_duration_seconds, uptime_percentage,
                        last_successful_run, updated_at
                    ) VALUES (
                        :id, :daemon_id, NULL, NULL,
                        0, 0, NULL,
                        NULL, 0, 0,
                        0, 0, 0,
                        100.0, NULL, 100.0,
                        NULL, :updated_at
                    )
                """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "daemon_id": daemon_id,
                    "updated_at": datetime.now(timezone.utc),
                },
            )


def downgrade() -> None:
    """Remove all daemon_status records."""
    # This is safe as the table will be dropped in the parent migration's downgrade
    pass
