"""Scheduled task model for recurring job management."""

from datetime import datetime
from typing import Any, Dict, Optional

# Note: Install types-croniter stub package for type checking
from croniter import croniter  # type: ignore[import-untyped]
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
)

from app.models.base import BaseModel


class ScheduledTask(BaseModel):
    """
    Model for managing scheduled tasks that run on a cron schedule.

    Tasks can be sync operations, analysis runs, or other recurring jobs.
    """

    # Auto-increment primary key
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Task identification
    name = Column(String, nullable=False, unique=True, index=True)
    task_type = Column(
        String, nullable=False, index=True
    )  # sync, analysis, cleanup, etc.

    # Scheduling
    schedule = Column(String, nullable=False)  # Cron expression
    config = Column(JSON, nullable=False, default=dict)  # Task-specific configuration
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # Execution tracking
    last_run = Column(DateTime(timezone=True), nullable=True, index=True)
    next_run = Column(DateTime(timezone=True), nullable=True, index=True)
    last_job_id = Column(String, nullable=True)  # Reference to last Job created

    # Indexes for common queries
    __table_args__ = (
        Index("idx_scheduled_task_enabled_next", "enabled", "next_run"),
        Index("idx_scheduled_task_type_enabled", "task_type", "enabled"),
    )

    def is_valid_schedule(self) -> bool:
        """Check if the cron schedule is valid."""
        try:
            croniter(self.schedule)
            return True
        except (ValueError, TypeError):
            return False

    def calculate_next_run(self, base_time: Optional[datetime] = None) -> datetime:
        """
        Calculate the next run time based on the cron schedule.

        Args:
            base_time: Base time to calculate from (defaults to now)

        Returns:
            Next run datetime
        """
        if not self.is_valid_schedule():
            raise ValueError(f"Invalid cron schedule: {self.schedule}")

        base = base_time or datetime.utcnow()
        cron = croniter(self.schedule, base)
        return cron.get_next(datetime)  # type: ignore[no-any-return]

    def update_next_run(self, base_time: Optional[datetime] = None) -> None:
        """Update the next_run field based on the schedule."""
        self.next_run = self.calculate_next_run(base_time)  # type: ignore[assignment]

    def mark_executed(self, job_id: str) -> None:
        """
        Mark task as executed.

        Args:
            job_id: ID of the job that was created
        """
        self.last_run = datetime.utcnow()  # type: ignore[assignment]
        self.last_job_id = job_id  # type: ignore[assignment]
        self.update_next_run(self.last_run)  # type: ignore[arg-type]

    def should_run_now(self, buffer_seconds: int = 60) -> bool:
        """
        Check if task should run now.

        Args:
            buffer_seconds: Grace period in seconds

        Returns:
            True if task should run
        """
        if not self.enabled or not self.next_run:
            return False

        now = datetime.utcnow()
        # Add buffer to account for scheduling delays
        return bool(self.next_run <= now)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default) if self.config else default

    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if self.config is None:
            self.config = {}
        self.config[key] = value

    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        data = super().to_dict(exclude)

        # Add computed fields
        data["is_valid_schedule"] = self.is_valid_schedule()
        data["should_run"] = self.should_run_now()

        # Add time until next run
        if self.next_run:
            seconds_until = (self.next_run - datetime.utcnow()).total_seconds()
            data["seconds_until_next_run"] = max(0, seconds_until)

        return data
