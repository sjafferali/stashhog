"""Tests for repository layer to improve coverage."""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.models import Job
from app.models.job import JobStatus, JobType
from app.repositories.job_repository import JobRepository


class TestJobRepository:
    """Test JobRepository functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock(spec=Session)
        db.execute = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        return db

    @pytest.fixture
    def job_repo(self):
        """Create JobRepository instance."""
        return JobRepository()

    @pytest.mark.asyncio
    async def test_create_job(self, job_repo, mock_db):
        """Test creating a new job."""
        job_id = "test-job-123"
        job_type = JobType.SYNC
        metadata = {"target": "scenes"}

        # Create a mock job to return
        mock_job = Mock(spec=Job)
        mock_job.id = job_id
        mock_job.type = job_type
        mock_job.status = JobStatus.PENDING
        mock_job.progress = 0
        mock_job.job_metadata = metadata

        # Set up refresh to update the mock
        mock_db.refresh = Mock(side_effect=lambda x: setattr(x, "id", job_id))

        job = await job_repo.create_job(job_id, job_type, mock_db, metadata)

        assert isinstance(job, Job)
        assert job.type == job_type
        assert job.status == JobStatus.PENDING
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, job_repo, mock_db):
        """Test getting job by ID."""
        job = Mock(spec=Job, id="job123", type=JobType.ANALYSIS)

        mock_db.query.return_value.filter.return_value.first.return_value = job

        result = await job_repo.get_job("job123", mock_db)

        assert result == job
        assert mock_db.query.called

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, job_repo, mock_db):
        """Test getting non-existent job."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await job_repo.get_job("nonexistent", mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_jobs(self, job_repo, mock_db):
        """Test listing jobs with filters."""
        jobs = [
            Mock(spec=Job, id="j1", type=JobType.SYNC, status=JobStatus.COMPLETED),
            Mock(spec=Job, id="j2", type=JobType.SYNC, status=JobStatus.RUNNING),
        ]

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = jobs

        # Test with filters
        result = await job_repo.list_jobs(
            mock_db, job_type=JobType.SYNC, status=JobStatus.RUNNING, limit=10
        )

        assert len(result) == 2
        assert mock_db.query.called

    @pytest.mark.asyncio
    async def test_update_job(self, job_repo, mock_db):
        """Test updating a job."""
        job = Mock(spec=Job, id="job123", status=JobStatus.PENDING)

        mock_db.query.return_value.filter.return_value.first.return_value = job

        await job_repo.update_job_status(
            "job123", JobStatus.RUNNING, mock_db, progress=50
        )

        assert job.status == JobStatus.RUNNING
        assert job.progress == 50
        mock_db.commit.assert_called_once()

    # Delete method doesn't exist in JobRepository, skip this test
    # def test_delete_job - removed

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, job_repo, mock_db):
        """Test getting active jobs."""
        active_jobs = [
            Mock(spec=Job, id="j1", status=JobStatus.RUNNING),
            Mock(spec=Job, id="j2", status=JobStatus.PENDING),
        ]

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = active_jobs

        result = await job_repo.get_active_jobs(mock_db)

        assert len(result) == 2
        assert all(j.status in [JobStatus.RUNNING, JobStatus.PENDING] for j in result)

    # get_by_type method doesn't exist in JobRepository, skip this test
    # def test_get_jobs_by_type - removed

    # update_progress method doesn't exist, use update_job_status instead
    # def test_update_job_progress - removed

    @pytest.mark.asyncio
    async def test_mark_job_completed(self, job_repo, mock_db):
        """Test marking job as completed."""
        job = Mock(spec=Job, id="job123", status=JobStatus.RUNNING)

        mock_db.query.return_value.filter.return_value.first.return_value = job

        await job_repo.update_job_status(
            "job123",
            JobStatus.COMPLETED,
            mock_db,
            progress=100,
            result={"processed": 100},
        )

        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.result == {"processed": 100}
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_job_failed(self, job_repo, mock_db):
        """Test marking job as failed."""
        job = Mock(spec=Job, id="job123", status=JobStatus.RUNNING)

        mock_db.query.return_value.filter.return_value.first.return_value = job

        await job_repo.update_job_status(
            "job123", JobStatus.FAILED, mock_db, error="Database connection error"
        )

        assert job.status == JobStatus.FAILED
        assert job.error == "Database connection error"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(self, job_repo, mock_db):
        """Test cleaning up old completed jobs."""
        # Mock the query chain for delete operation
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 5  # Simulate 5 deleted jobs

        deleted_count = await job_repo.cleanup_old_jobs(mock_db, days=30)

        # Verify the cleanup query was executed
        assert deleted_count == 5
        mock_db.query.assert_called_with(Job)
        mock_query.delete.assert_called()
        mock_db.commit.assert_called()


# TestSyncRepository tests removed - methods don't exist in actual implementation
