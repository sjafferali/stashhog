"""Tests for the ScheduledTask model."""

from datetime import datetime

import pytest
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_task import ScheduledTask


class TestScheduledTaskModel:
    """Test ScheduledTask model operations."""

    async def test_create_scheduled_task(self, test_async_session: AsyncSession):
        """Test creating a scheduled task."""
        task = ScheduledTask(
            name="Daily Sync",
            task_type="sync",
            schedule="0 2 * * *",  # Daily at 2 AM
            config={"sync_type": "full", "retry_count": 3},
            enabled=True,
        )

        test_async_session.add(task)
        await test_async_session.commit()
        await test_async_session.refresh(task)

        assert task.id is not None
        assert task.name == "Daily Sync"
        assert task.task_type == "sync"
        assert task.schedule == "0 2 * * *"
        assert task.config == {"sync_type": "full", "retry_count": 3}
        assert task.enabled is True
        assert task.last_run is None
        assert task.next_run is None
        assert task.last_job_id is None

    async def test_unique_name_constraint(self, test_async_session: AsyncSession):
        """Test that task names must be unique."""
        # Create first task
        task1 = ScheduledTask(
            name="Unique Task", task_type="sync", schedule="* * * * *"
        )
        test_async_session.add(task1)
        await test_async_session.commit()

        # Try to create duplicate
        task2 = ScheduledTask(
            name="Unique Task", task_type="analysis", schedule="0 * * * *"
        )
        test_async_session.add(task2)

        with pytest.raises(IntegrityError):
            await test_async_session.commit()

        await test_async_session.rollback()

    async def test_is_valid_schedule(self, test_async_session: AsyncSession):
        """Test schedule validation."""
        # Valid schedules
        valid_task = ScheduledTask(
            name="Valid Schedule",
            task_type="sync",
            schedule="0 */6 * * *",  # Every 6 hours
        )
        assert valid_task.is_valid_schedule() is True

        # Invalid schedules
        invalid_task = ScheduledTask(
            name="Invalid Schedule", task_type="sync", schedule="invalid cron"
        )
        assert invalid_task.is_valid_schedule() is False

        # Empty schedule
        empty_task = ScheduledTask(name="Empty Schedule", task_type="sync", schedule="")
        assert empty_task.is_valid_schedule() is False

    @freeze_time("2024-01-15 10:00:00")
    async def test_calculate_next_run(self, test_async_session: AsyncSession):
        """Test next run calculation."""
        # Hourly task
        hourly_task = ScheduledTask(
            name="Hourly Task",
            task_type="sync",
            schedule="0 * * * *",  # Every hour at minute 0
        )

        next_run = hourly_task.calculate_next_run()
        expected = datetime(2024, 1, 15, 11, 0, 0)
        assert next_run == expected

        # Daily task
        daily_task = ScheduledTask(
            name="Daily Task", task_type="sync", schedule="0 14 * * *"  # Daily at 2 PM
        )

        next_run = daily_task.calculate_next_run()
        expected = datetime(2024, 1, 15, 14, 0, 0)
        assert next_run == expected

        # Task with specific base time
        base_time = datetime(2024, 1, 15, 16, 30, 0)
        next_run = daily_task.calculate_next_run(base_time)
        expected = datetime(2024, 1, 16, 14, 0, 0)  # Next day
        assert next_run == expected

    async def test_calculate_next_run_invalid_schedule(
        self, test_async_session: AsyncSession
    ):
        """Test next run calculation with invalid schedule."""
        task = ScheduledTask(name="Invalid Task", task_type="sync", schedule="invalid")

        with pytest.raises(ValueError, match="Invalid cron schedule"):
            task.calculate_next_run()

    @freeze_time("2024-01-15 10:00:00")
    async def test_update_next_run(self, test_async_session: AsyncSession):
        """Test updating next run time."""
        task = ScheduledTask(
            name="Update Next Run",
            task_type="sync",
            schedule="30 * * * *",  # Every hour at minute 30
        )

        task.update_next_run()
        expected = datetime(2024, 1, 15, 10, 30, 0)
        assert task.next_run == expected

        # Update with specific base time
        base = datetime(2024, 1, 15, 11, 45, 0)
        task.update_next_run(base)
        expected = datetime(2024, 1, 15, 12, 30, 0)
        assert task.next_run == expected

    @freeze_time("2024-01-15 10:00:00")
    async def test_mark_executed(self, test_async_session: AsyncSession):
        """Test marking task as executed."""
        task = ScheduledTask(
            name="Executed Task", task_type="sync", schedule="0 * * * *"  # Hourly
        )

        task.mark_executed("job-123")

        assert task.last_run == datetime(2024, 1, 15, 10, 0, 0)
        assert task.last_job_id == "job-123"
        assert task.next_run == datetime(2024, 1, 15, 11, 0, 0)

    @freeze_time("2024-01-15 10:00:00")
    async def test_should_run_now(self, test_async_session: AsyncSession):
        """Test checking if task should run."""
        # Task that should run (past due)
        task1 = ScheduledTask(
            name="Past Due Task",
            task_type="sync",
            schedule="* * * * *",
            enabled=True,
            next_run=datetime(2024, 1, 15, 9, 30, 0),  # 30 minutes ago
        )
        assert task1.should_run_now() is True

        # Task that should not run (future)
        task2 = ScheduledTask(
            name="Future Task",
            task_type="sync",
            schedule="* * * * *",
            enabled=True,
            next_run=datetime(2024, 1, 15, 11, 0, 0),  # 1 hour in future
        )
        assert task2.should_run_now() is False

        # Disabled task
        task3 = ScheduledTask(
            name="Disabled Task",
            task_type="sync",
            schedule="* * * * *",
            enabled=False,
            next_run=datetime(2024, 1, 15, 9, 30, 0),  # Past due but disabled
        )
        assert task3.should_run_now() is False

        # Task with no next_run
        task4 = ScheduledTask(
            name="No Next Run",
            task_type="sync",
            schedule="* * * * *",
            enabled=True,
            next_run=None,
        )
        assert task4.should_run_now() is False

    async def test_config_operations(self, test_async_session: AsyncSession):
        """Test configuration get/set operations."""
        task = ScheduledTask(
            name="Config Task",
            task_type="sync",
            schedule="* * * * *",
            config={"key1": "value1", "key2": 42},
        )

        # Get existing values
        assert task.get_config_value("key1") == "value1"
        assert task.get_config_value("key2") == 42

        # Get non-existent value with default
        assert task.get_config_value("missing") is None
        assert task.get_config_value("missing", "default") == "default"

        # Set new value
        task.set_config_value("key3", {"nested": "data"})
        assert task.config["key3"] == {"nested": "data"}

        # Update existing value
        task.set_config_value("key1", "updated")
        assert task.config["key1"] == "updated"

    async def test_config_operations_null_config(
        self, test_async_session: AsyncSession
    ):
        """Test config operations when config is initially null."""
        task = ScheduledTask(
            name="Null Config Task", task_type="sync", schedule="* * * * *"
        )
        task.config = None

        # Get from null config
        assert task.get_config_value("key") is None
        assert task.get_config_value("key", "default") == "default"

        # Set to null config (should initialize)
        task.set_config_value("key", "value")
        assert task.config == {"key": "value"}

    @freeze_time("2024-01-15 10:00:00")
    async def test_to_dict(self, test_async_session: AsyncSession):
        """Test converting task to dictionary."""
        task = ScheduledTask(
            name="Dict Task",
            task_type="analysis",
            schedule="0 * * * *",
            config={"batch_size": 100},
            enabled=True,
            next_run=datetime(2024, 1, 15, 11, 0, 0),
            last_run=datetime(2024, 1, 15, 9, 0, 0),
            last_job_id="prev-job",
        )

        data = task.to_dict()

        assert data["name"] == "Dict Task"
        assert data["task_type"] == "analysis"
        assert data["schedule"] == "0 * * * *"
        assert data["config"] == {"batch_size": 100}
        assert data["enabled"] is True
        assert data["is_valid_schedule"] is True
        assert data["should_run"] is False
        assert data["seconds_until_next_run"] == 3600  # 1 hour

        # Test with exclusions
        data_excluded = task.to_dict(exclude={"config", "last_job_id"})
        assert "config" not in data_excluded
        assert "last_job_id" not in data_excluded
        assert "name" in data_excluded

    @freeze_time("2024-01-15 10:00:00")
    async def test_to_dict_past_due(self, test_async_session: AsyncSession):
        """Test to_dict with past due task."""
        task = ScheduledTask(
            name="Past Due Dict",
            task_type="sync",
            schedule="* * * * *",
            enabled=True,
            next_run=datetime(2024, 1, 15, 9, 30, 0),  # 30 minutes ago
        )

        data = task.to_dict()
        assert data["should_run"] is True
        assert data["seconds_until_next_run"] == 0  # Max of 0

    async def test_different_task_types(self, test_async_session: AsyncSession):
        """Test creating tasks with different types."""
        tasks = [
            ScheduledTask(
                name="Sync Task",
                task_type="sync",
                schedule="0 */4 * * *",
                config={"sync_entities": ["scenes", "performers"]},
            ),
            ScheduledTask(
                name="Analysis Task",
                task_type="analysis",
                schedule="0 3 * * *",
                config={"analyze_unanalyzed": True, "batch_size": 50},
            ),
            ScheduledTask(
                name="Cleanup Task",
                task_type="cleanup",
                schedule="0 0 * * 0",  # Weekly on Sunday
                config={"remove_orphans": True, "vacuum": True},
            ),
            ScheduledTask(
                name="Report Task",
                task_type="report",
                schedule="0 9 1 * *",  # Monthly on 1st at 9 AM
                config={"email_to": ["admin@example.com"], "format": "pdf"},
            ),
        ]

        test_async_session.add_all(tasks)
        await test_async_session.commit()

        # Query by task type
        result = await test_async_session.execute(
            select(ScheduledTask).filter(ScheduledTask.task_type == "sync")
        )
        sync_tasks = result.scalars().all()
        assert len(sync_tasks) == 1
        assert sync_tasks[0].name == "Sync Task"

    async def test_schedule_patterns(self, test_async_session: AsyncSession):
        """Test various cron schedule patterns."""
        patterns = [
            ("*/5 * * * *", "Every 5 minutes"),
            ("0 */2 * * *", "Every 2 hours"),
            ("0 0 * * *", "Daily at midnight"),
            ("0 0 * * 1", "Weekly on Monday"),
            ("0 0 1 * *", "Monthly on 1st"),
            ("30 14 * * 1-5", "Weekdays at 2:30 PM"),
            ("0 0,12 * * *", "Twice daily at midnight and noon"),
        ]

        for schedule, description in patterns:
            task = ScheduledTask(
                name=f"Pattern: {description}", task_type="test", schedule=schedule
            )
            assert task.is_valid_schedule() is True

    async def test_persistence_and_query(self, test_async_session: AsyncSession):
        """Test persisting and querying scheduled tasks."""
        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = ScheduledTask(
                name=f"Task {i}",
                task_type="sync" if i % 2 == 0 else "analysis",
                schedule=f"{i} * * * *",
                enabled=i < 3,  # First 3 enabled
            )
            tasks.append(task)

        test_async_session.add_all(tasks)
        await test_async_session.commit()

        # Query enabled tasks
        result = await test_async_session.execute(
            select(ScheduledTask).filter(ScheduledTask.enabled.is_(True))
        )
        enabled_tasks = result.scalars().all()
        assert len(enabled_tasks) == 3

        # Query by task type
        result = await test_async_session.execute(
            select(ScheduledTask).filter(ScheduledTask.task_type == "analysis")
        )
        analysis_tasks = result.scalars().all()
        assert len(analysis_tasks) == 2

    async def test_base_model_fields(self, test_async_session: AsyncSession):
        """Test that ScheduledTask inherits BaseModel fields correctly."""
        task = ScheduledTask(
            name="Base Model Task", task_type="sync", schedule="* * * * *"
        )

        test_async_session.add(task)
        await test_async_session.commit()
        await test_async_session.refresh(task)

        # BaseModel should provide created_at and updated_at
        assert hasattr(task, "created_at")
        assert hasattr(task, "updated_at")
        assert task.created_at is not None
        assert task.updated_at is not None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)
