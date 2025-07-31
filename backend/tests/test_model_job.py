"""Tests for the Job model."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.models.job import Job, JobStatus, JobType


@pytest.fixture
def job():
    """Create a test job."""
    job = Job(
        id=str(uuid.uuid4()),
        type=JobType.SYNC,
        status=JobStatus.PENDING,
        progress=0,
        total_items=None,
        processed_items=0,
        result=None,
        error=None,
        job_metadata={},
    )
    return job


class TestJob:
    """Test Job model functionality."""

    def test_initialization(self):
        """Test Job initialization."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            type=JobType.ANALYSIS,
            status=JobStatus.PENDING,
            progress=0,
            total_items=100,
            processed_items=0,
            result=None,
            error=None,
            job_metadata={"key": "value"},
        )
        assert job.id == job_id
        assert job.type == JobType.ANALYSIS
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        assert job.total_items == 100
        assert job.processed_items == 0
        assert job.result is None
        assert job.error is None
        assert job.job_metadata == {"key": "value"}
        assert job.started_at is None
        assert job.completed_at is None

    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
        assert JobStatus.IN_PROGRESS == "running"  # Alias

    def test_job_type_enum(self):
        """Test JobType enum values."""
        assert JobType.SYNC == "sync"
        assert JobType.SYNC_SCENES == "sync_scenes"
        assert JobType.ANALYSIS == "analysis"
        assert JobType.APPLY_PLAN == "apply_plan"
        assert JobType.GENERATE_DETAILS == "generate_details"
        assert JobType.EXPORT == "export"
        assert JobType.IMPORT == "import"
        assert JobType.CLEANUP == "cleanup"

    def test_update_progress_with_both_values(self, job):
        """Test update_progress with both processed and total."""
        job.update_progress(processed=25, total=100)
        assert job.processed_items == 25
        assert job.total_items == 100
        assert job.progress == 25

    def test_update_progress_processed_only(self, job):
        """Test update_progress with only processed."""
        job.total_items = 50
        job.update_progress(processed=10)
        assert job.processed_items == 10
        assert job.total_items == 50
        assert job.progress == 20

    def test_update_progress_total_only(self, job):
        """Test update_progress with only total."""
        job.processed_items = 30
        job.update_progress(total=60)
        assert job.processed_items == 30
        assert job.total_items == 60
        assert job.progress == 50

    def test_update_progress_zero_total(self, job):
        """Test update_progress with zero total."""
        job.update_progress(processed=10, total=0)
        assert job.processed_items == 10
        assert job.total_items == 0
        assert job.progress == 0

    def test_update_progress_none_total(self, job):
        """Test update_progress with None total."""
        job.update_progress(processed=10, total=None)
        assert job.processed_items == 10
        assert job.total_items is None
        assert job.progress == 0

    def test_update_progress_complete(self, job):
        """Test update_progress when job is complete."""
        job.update_progress(processed=100, total=100)
        assert job.progress == 100

    def test_update_progress_over_100_percent(self, job):
        """Test update_progress when processed exceeds total."""
        job.update_progress(processed=150, total=100)
        assert job.processed_items == 150
        assert job.total_items == 100
        assert job.progress == 150  # Allow over 100%

    def test_mark_started(self, job):
        """Test mark_started."""
        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            job.mark_started()

            assert job.status == JobStatus.RUNNING
            assert job.started_at == mock_now
            assert job.progress == 0

    def test_mark_completed_without_result(self, job):
        """Test mark_completed without result."""
        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            job.mark_completed()

            assert job.status == JobStatus.COMPLETED
            assert job.completed_at == mock_now
            assert job.progress == 100
            assert job.result is None

    def test_mark_completed_with_result(self, job):
        """Test mark_completed with result."""
        result_data = {"success": True, "count": 10}

        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            job.mark_completed(result_data)

            assert job.status == JobStatus.COMPLETED
            assert job.completed_at == mock_now
            assert job.progress == 100
            assert job.result == result_data

    def test_mark_failed(self, job):
        """Test mark_failed."""
        error_message = "Connection failed"

        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 15, 0, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            job.mark_failed(error_message)

            assert job.status == JobStatus.FAILED
            assert job.completed_at == mock_now
            assert job.error == error_message

    def test_mark_cancelled(self, job):
        """Test mark_cancelled."""
        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            job.mark_cancelled()

            assert job.status == JobStatus.CANCELLED
            assert job.completed_at == mock_now

    def test_get_duration_seconds_completed(self, job):
        """Test get_duration_seconds for completed job."""
        job.started_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job.completed_at = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)

        duration = job.get_duration_seconds()
        assert duration == 1845.0  # 30 minutes 45 seconds

    def test_get_duration_seconds_running(self, job):
        """Test get_duration_seconds for running job."""
        job.started_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job.completed_at = None

        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            duration = job.get_duration_seconds()
            assert duration == 330.0  # 5 minutes 30 seconds

    def test_get_duration_seconds_not_started(self, job):
        """Test get_duration_seconds for job not started."""
        job.started_at = None

        duration = job.get_duration_seconds()
        assert duration is None

    def test_is_running(self, job):
        """Test is_running."""
        job.status = JobStatus.PENDING
        assert job.is_running() is False

        job.status = JobStatus.RUNNING
        assert job.is_running() is True

        job.status = JobStatus.COMPLETED
        assert job.is_running() is False

    def test_is_finished(self, job):
        """Test is_finished."""
        job.status = JobStatus.PENDING
        assert job.is_finished() is False

        job.status = JobStatus.RUNNING
        assert job.is_finished() is False

        job.status = JobStatus.COMPLETED
        assert job.is_finished() is True

        job.status = JobStatus.FAILED
        assert job.is_finished() is True

        job.status = JobStatus.CANCELLED
        assert job.is_finished() is True

    def test_can_be_cancelled(self, job):
        """Test can_be_cancelled."""
        job.status = JobStatus.PENDING
        assert job.can_be_cancelled() is True

        job.status = JobStatus.RUNNING
        assert job.can_be_cancelled() is True

        job.status = JobStatus.COMPLETED
        assert job.can_be_cancelled() is False

        job.status = JobStatus.FAILED
        assert job.can_be_cancelled() is False

        job.status = JobStatus.CANCELLED
        assert job.can_be_cancelled() is False

    def test_add_result_data_empty_result(self, job):
        """Test add_result_data with empty result."""
        job.result = None
        job.add_result_data("count", 10)

        assert job.result == {"count": 10}

    def test_add_result_data_existing_result(self, job):
        """Test add_result_data with existing result."""
        job.result = {"status": "ok"}
        job.add_result_data("count", 10)

        assert job.result == {"status": "ok", "count": 10}

    def test_add_result_data_overwrite(self, job):
        """Test add_result_data overwriting existing key."""
        job.result = {"count": 5}
        job.add_result_data("count", 10)

        assert job.result == {"count": 10}

    def test_to_dict_basic(self, job):
        """Test to_dict basic functionality."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        with patch("app.models.job.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = mock_now

            result = job.to_dict()

            assert result["id"] == job.id
            assert result["type"] == JobType.SYNC
            assert result["status"] == JobStatus.RUNNING
            assert result["progress"] == 0
            assert result["duration_seconds"] == 300.0
            assert result["is_running"] is True
            assert result["is_finished"] is False
            assert result["can_cancel"] is True

    def test_to_dict_with_exclude(self, job):
        """Test to_dict with exclude parameter."""
        result = job.to_dict(exclude={"progress", "error"})

        assert "progress" not in result
        assert "error" not in result
        assert "duration_seconds" in result
        assert "is_running" in result

    def test_table_indexes(self):
        """Test that proper indexes are defined."""
        # Check that the table args define the expected indexes
        table_args = Job.__table_args__
        assert len(table_args) == 3

        # Check index names
        index_names = [idx.name for idx in table_args]
        assert "idx_job_type_status" in index_names
        assert "idx_job_status_created" in index_names
        assert "idx_job_completed" in index_names


class TestJobEdgeCases:
    """Test edge cases and error scenarios."""

    def test_default_id_generation(self):
        """Test that ID is generated if not provided."""
        job = Job(type=JobType.SYNC)
        # Can't test the actual UUID generation without database,
        # but we can verify the field exists
        assert hasattr(job, "id")

    def test_job_metadata_default(self):
        """Test job_metadata default value."""
        job = Job(type=JobType.SYNC)
        # Default is set by database, so in memory it might be None
        assert job.job_metadata is None or job.job_metadata == {}

    def test_progress_calculation_edge_cases(self, job):
        """Test progress calculation edge cases."""
        # Negative values
        job.update_progress(processed=-10, total=100)
        assert job.processed_items == -10
        assert job.progress == -10

        # Very large values
        job.update_progress(processed=1_000_000, total=1_000)
        assert job.progress == 100_000

    def test_duration_with_timezone_aware_dates(self, job):
        """Test duration calculation with timezone-aware dates."""
        job.started_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job.completed_at = datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        duration = job.get_duration_seconds()
        assert duration == 3600.0

    def test_job_state_transitions(self, job):
        """Test various job state transitions."""
        # Start from PENDING
        assert job.status == JobStatus.PENDING

        # Start the job
        job.mark_started()
        assert job.status == JobStatus.RUNNING

        # Complete the job
        job.mark_completed({"success": True})
        assert job.status == JobStatus.COMPLETED
        assert job.result == {"success": True}

    def test_failed_job_workflow(self, job):
        """Test failed job workflow."""
        job.mark_started()
        job.update_progress(processed=50, total=100)

        error_msg = "Database connection lost"
        job.mark_failed(error_msg)

        assert job.status == JobStatus.FAILED
        assert job.error == error_msg
        assert job.progress == 50  # Progress not reset on failure
        assert job.is_finished() is True
        assert job.can_be_cancelled() is False

    def test_cancelled_job_workflow(self, job):
        """Test cancelled job workflow."""
        job.mark_started()
        job.update_progress(processed=30, total=100)

        job.mark_cancelled()

        assert job.status == JobStatus.CANCELLED
        assert job.progress == 30  # Progress not reset on cancel
        assert job.is_finished() is True
        assert job.can_be_cancelled() is False

    def test_complex_result_data(self, job):
        """Test complex result data structures."""
        job.add_result_data(
            "stats",
            {
                "total": 100,
                "processed": 95,
                "errors": ["Error 1", "Error 2"],
                "metadata": {"source": "test"},
            },
        )

        assert job.result["stats"]["total"] == 100
        assert len(job.result["stats"]["errors"]) == 2
        assert job.result["stats"]["metadata"]["source"] == "test"

    def test_unicode_in_error_message(self, job):
        """Test unicode characters in error message."""
        error_msg = "Failed to process: ñoño café ☕"
        job.mark_failed(error_msg)

        assert job.error == error_msg

    def test_very_long_error_message(self, job):
        """Test very long error message."""
        error_msg = "Error: " + "A" * 10000
        job.mark_failed(error_msg)

        assert len(job.error) == 10007
