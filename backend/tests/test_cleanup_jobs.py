"""Tests for cleanup job functions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cancellation import CancellationToken
from app.jobs.cleanup_jobs import (
    cleanup_stale_jobs,
    register_cleanup_jobs,
)
from app.models.job import Job, JobStatus, JobType
from app.services.job_service import JobService


class TestCleanupJobs:
    """Test cleanup job functions."""

    @pytest.fixture
    def mock_cancellation_token(self):
        """Create a mock cancellation token."""
        token = Mock(spec=CancellationToken)
        # Ensure is_cancelled is a property, not a method
        token.is_cancelled = False
        return token

    @pytest.fixture
    def mock_progress_callback(self):
        """Create a mock progress callback."""
        return AsyncMock()

    @pytest.fixture
    def mock_stale_job(self):
        """Create a mock stale job."""
        job = Mock(spec=Job)
        job.id = "stale-job-123"
        job.type = JobType.SYNC
        job.status = JobStatus.RUNNING
        job.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        job.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        job.progress = 50
        job.job_metadata = {"task_id": "task-123"}
        return job

    @pytest.fixture
    def mock_old_completed_job(self):
        """Create a mock old completed job."""
        job = Mock(spec=Job)
        job.id = "old-job-456"
        job.type = JobType.SYNC
        job.status = JobStatus.COMPLETED
        job.created_at = datetime.now(timezone.utc) - timedelta(days=40)
        job.completed_at = datetime.now(timezone.utc) - timedelta(days=40)
        return job

    async def test_cleanup_stale_jobs_with_cancellation_token(
        self, mock_cancellation_token, mock_progress_callback, mock_stale_job
    ):
        """Test cleanup job handles cancellation token correctly."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_stale_job]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        # Mock task queue
        mock_task = Mock()
        mock_task.status = "completed"  # Not running
        mock_task_queue = Mock()
        mock_task_queue.get_task.return_value = mock_task

        # Test that cancellation token is checked during iteration
        mock_cancellation_token.is_cancelled = True

        # Create async context manager mock
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_db
        mock_session_cm.__aexit__.return_value = None

        with patch(
            "app.jobs.cleanup_jobs.AsyncSessionLocal", return_value=mock_session_cm
        ):
            with patch(
                "app.jobs.cleanup_jobs.get_task_queue", return_value=mock_task_queue
            ):
                with patch("app.jobs.cleanup_jobs._cleanup_old_jobs", return_value=1):
                    with patch(
                        "app.jobs.cleanup_jobs._cleanup_stuck_pending_plans",
                        return_value=(0, None),
                    ):
                        # Act
                        result = await cleanup_stale_jobs(
                            job_id="cleanup-job-789",
                            progress_callback=mock_progress_callback,
                            cancellation_token=mock_cancellation_token,
                        )

        # Assert
        assert result["status"] == "completed"
        assert result["cleaned_jobs"] == 0  # Should stop before processing any jobs
        # Verify we tried to check the cancellation token property, not call it as a method
        # The mock will raise AttributeError if we try to call is_cancelled()

    async def test_cleanup_stale_jobs_property_not_method(
        self, mock_cancellation_token, mock_progress_callback, mock_stale_job
    ):
        """Test that is_cancelled is accessed as a property, not called as a method."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        # Include a job so the cancellation check is reached
        mock_result.scalars.return_value.all.return_value = [mock_stale_job]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Mock task queue
        mock_task_queue = Mock()
        mock_task_queue.get_task.return_value = None

        # Make is_cancelled property that would fail if called as method
        # We'll use a special mock that tracks access
        access_tracker = {"accessed_as_property": False, "called_as_method": False}

        class SpecialMock:
            @property
            def is_cancelled(self):
                access_tracker["accessed_as_property"] = True
                return False

        mock_cancellation_token = SpecialMock()
        # If someone tries to call is_cancelled(), it would fail because properties can't be called

        # Create async context manager mock
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_db
        mock_session_cm.__aexit__.return_value = None

        with patch(
            "app.jobs.cleanup_jobs.AsyncSessionLocal", return_value=mock_session_cm
        ):
            with patch(
                "app.jobs.cleanup_jobs.get_task_queue", return_value=mock_task_queue
            ):
                with patch("app.jobs.cleanup_jobs._cleanup_old_jobs", return_value=1):
                    with patch(
                        "app.jobs.cleanup_jobs._cleanup_stuck_pending_plans",
                        return_value=(0, None),
                    ):
                        # Act - should not raise TypeError
                        result = await cleanup_stale_jobs(
                            job_id="cleanup-job-test",
                            progress_callback=mock_progress_callback,
                            cancellation_token=mock_cancellation_token,
                        )

        # Assert
        assert result["status"] == "completed"
        assert "error" not in result or result.get("error") is None
        assert access_tracker["accessed_as_property"]  # Verify property was accessed

    async def test_cleanup_processes_stale_jobs(
        self, mock_cancellation_token, mock_progress_callback, mock_stale_job
    ):
        """Test cleanup successfully processes stale jobs."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_stale_job]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Mock task queue - task is not actually running
        mock_task = Mock()
        mock_task.status = "completed"
        mock_task_queue = Mock()
        mock_task_queue.get_task.return_value = mock_task

        mock_cancellation_token.is_cancelled = False

        # Create async context manager mock
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_db
        mock_session_cm.__aexit__.return_value = None

        with patch(
            "app.jobs.cleanup_jobs.AsyncSessionLocal", return_value=mock_session_cm
        ):
            with patch(
                "app.jobs.cleanup_jobs.get_task_queue", return_value=mock_task_queue
            ):
                with patch("app.jobs.cleanup_jobs._cleanup_old_jobs", return_value=1):
                    with patch(
                        "app.jobs.cleanup_jobs._cleanup_stuck_pending_plans",
                        return_value=(0, None),
                    ):
                        # Act
                        result = await cleanup_stale_jobs(
                            job_id="cleanup-job-123",
                            progress_callback=mock_progress_callback,
                            cancellation_token=mock_cancellation_token,
                        )

        # Assert
        assert result["status"] == "completed"
        assert result["cleaned_jobs"] == 1
        assert mock_stale_job.status == JobStatus.FAILED
        assert "timed out" in mock_stale_job.error

    async def test_cleanup_without_cancellation_token(
        self, mock_progress_callback, mock_stale_job
    ):
        """Test cleanup works when cancellation token is None."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_stale_job]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Mock task queue
        mock_task_queue = Mock()
        mock_task_queue.get_task.return_value = None

        # Create async context manager mock
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_db
        mock_session_cm.__aexit__.return_value = None

        with patch(
            "app.jobs.cleanup_jobs.AsyncSessionLocal", return_value=mock_session_cm
        ):
            with patch(
                "app.jobs.cleanup_jobs.get_task_queue", return_value=mock_task_queue
            ):
                with patch("app.jobs.cleanup_jobs._cleanup_old_jobs", return_value=1):
                    with patch(
                        "app.jobs.cleanup_jobs._cleanup_stuck_pending_plans",
                        return_value=(0, None),
                    ):
                        # Act
                        result = await cleanup_stale_jobs(
                            job_id="cleanup-job-456",
                            progress_callback=mock_progress_callback,
                            cancellation_token=None,  # No cancellation token
                        )

        # Assert
        assert result["status"] == "completed"
        assert result["cleaned_jobs"] == 1

    def test_register_cleanup_jobs(self):
        """Test cleanup jobs registration."""
        # Arrange
        mock_job_service = Mock(spec=JobService)

        # Act
        register_cleanup_jobs(mock_job_service)

        # Assert
        mock_job_service.register_handler.assert_called_once_with(
            JobType.CLEANUP, cleanup_stale_jobs
        )
