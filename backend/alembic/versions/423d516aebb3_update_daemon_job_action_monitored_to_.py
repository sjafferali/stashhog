"""update_daemon_job_action_monitored_to_finished

Revision ID: 423d516aebb3
Revises: ab03494cf24d
Create Date: 2025-08-12 20:41:45.167665

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "423d516aebb3"
down_revision: Union[str, None] = "ab03494cf24d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update all existing MONITORED records to FINISHED in daemon_job_history
    op.execute(
        """
        UPDATE daemon_job_history
        SET action = 'FINISHED'
        WHERE action = 'MONITORED'
    """
    )

    # Log the migration
    op.execute(
        """
        SELECT COUNT(*) FROM daemon_job_history WHERE action = 'MONITORED'
    """
    )


def downgrade() -> None:
    # Revert FINISHED back to MONITORED if needed
    op.execute(
        """
        UPDATE daemon_job_history
        SET action = 'MONITORED'
        WHERE action = 'FINISHED'
    """
    )
