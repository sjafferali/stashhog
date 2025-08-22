"""add_daemon_observability_tables

Revision ID: 50fefb17d3ad
Revises: 743ce2c67347
Create Date: 2025-08-21 15:32:55.194942

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50fefb17d3ad"
down_revision: Union[str, None] = "743ce2c67347"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create daemon_errors table
    op.create_table(
        "daemon_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_type", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_daemon_errors_daemon_id_last_seen",
        "daemon_errors",
        ["daemon_id", "last_seen"],
        unique=False,
    )
    op.create_index(
        "idx_daemon_errors_error_type", "daemon_errors", ["error_type"], unique=False
    )
    op.create_index(
        "idx_daemon_errors_resolved", "daemon_errors", ["resolved"], unique=False
    )

    # Create daemon_activities table
    op.create_table(
        "daemon_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_daemon_activities_activity_type",
        "daemon_activities",
        ["activity_type"],
        unique=False,
    )
    op.create_index(
        "idx_daemon_activities_daemon_id_created_at",
        "daemon_activities",
        ["daemon_id", "created_at"],
        unique=False,
    )

    # Create daemon_metrics table
    op.create_table(
        "daemon_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metric_unit", sa.String(length=50), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daemon_id", "metric_name", "timestamp", name="uq_daemon_metric"
        ),
    )
    op.create_index(
        "idx_daemon_metrics_daemon_id_timestamp",
        "daemon_metrics",
        ["daemon_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "idx_daemon_metrics_metric_name",
        "daemon_metrics",
        ["metric_name"],
        unique=False,
    )

    # Create daemon_alerts table
    op.create_table(
        "daemon_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("threshold_unit", sa.String(length=50), nullable=True),
        sa.Column("notification_method", sa.String(length=50), nullable=False),
        sa.Column("notification_config", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_triggered", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("daemon_id", "alert_type", name="uq_daemon_alert"),
    )
    op.create_index(
        "idx_daemon_alerts_enabled", "daemon_alerts", ["enabled"], unique=False
    )

    # Create daemon_status table
    op.create_table(
        "daemon_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_activity", sa.String(length=255), nullable=True),
        sa.Column("current_progress", sa.Float(), nullable=True),
        sa.Column("items_processed", sa.Integer(), nullable=False),
        sa.Column("items_pending", sa.Integer(), nullable=False),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("last_error_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_count_24h", sa.Integer(), nullable=False),
        sa.Column("warning_count_24h", sa.Integer(), nullable=False),
        sa.Column("jobs_launched_24h", sa.Integer(), nullable=False),
        sa.Column("jobs_completed_24h", sa.Integer(), nullable=False),
        sa.Column("jobs_failed_24h", sa.Integer(), nullable=False),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("avg_job_duration_seconds", sa.Float(), nullable=True),
        sa.Column("uptime_percentage", sa.Float(), nullable=False),
        sa.Column("last_successful_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["daemon_id"], ["daemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("daemon_id", name="uq_daemon_status"),
    )


def downgrade() -> None:
    op.drop_table("daemon_status")
    op.drop_index("idx_daemon_alerts_enabled", table_name="daemon_alerts")
    op.drop_table("daemon_alerts")
    op.drop_index("idx_daemon_metrics_metric_name", table_name="daemon_metrics")
    op.drop_index("idx_daemon_metrics_daemon_id_timestamp", table_name="daemon_metrics")
    op.drop_table("daemon_metrics")
    op.drop_index(
        "idx_daemon_activities_daemon_id_created_at", table_name="daemon_activities"
    )
    op.drop_index("idx_daemon_activities_activity_type", table_name="daemon_activities")
    op.drop_table("daemon_activities")
    op.drop_index("idx_daemon_errors_resolved", table_name="daemon_errors")
    op.drop_index("idx_daemon_errors_error_type", table_name="daemon_errors")
    op.drop_index("idx_daemon_errors_daemon_id_last_seen", table_name="daemon_errors")
    op.drop_table("daemon_errors")
