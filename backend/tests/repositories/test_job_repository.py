"""Tests for JobRepository."""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import job_repository


class TestJobRepository:
    """Test cases for JobRepository."""

    @pytest.mark.asyncio
    async def test_create_job_async(self, test_async_session: AsyncSession) -> None:
        """Test creating a job with async session."""
        job_id = "test-job-123"
        job_type = JobType.SYNC
        metadata = {"test": "data", "count": 5}

        job = await job_repository.create_job(
            job_id=job_id, job_type=job_type, db=test_async_session, metadata=metadata
        )

        assert job.id == job_id
        assert job.type == job_type.value
        assert job.status == JobStatus.PENDING.value
        assert job.progress == 0
        assert job.job_metadata == metadata
        assert job.created_at is not None
        assert job.started_at is None
        assert job.completed_at is None

    def test_create_job_sync(self, test_session: Session) -> None:
        """Test creating a job with sync session."""
        job_id = "test-job-456"
        job_type = JobType.ANALYSIS

        # Run async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        job = loop.run_until_complete(
            job_repository.create_job(job_id=job_id, job_type=job_type, db=test_session)
        )
        loop.close()

        assert job.id == job_id
        assert job.type == job_type.value
        assert job.status == JobStatus.PENDING.value
        assert job.job_metadata == {}

    @pytest.mark.asyncio
    async def test_get_job(self, test_async_session: AsyncSession) -> None:
        """Test getting a job by ID."""
        # Create a job first
        job_id = "test-get-job"
        created_job = await job_repository.create_job(
            job_id=job_id, job_type=JobType.SYNC, db=test_async_session
        )

        # Get the job
        fetched_job = await job_repository.get_job(job_id=job_id, db=test_async_session)

        assert fetched_job is not None
        assert fetched_job.id == created_job.id
        assert fetched_job.type == created_job.type

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, test_async_session: AsyncSession) -> None:
        """Test getting a non-existent job."""
        job = await job_repository.get_job(job_id="non-existent", db=test_async_session)
        assert job is None

    @pytest.mark.asyncio
    async def test_update_job_status(self, test_async_session: AsyncSession) -> None:
        """Test updating job status."""
        # Create a job
        job_id = "test-update-status"
        await job_repository.create_job(
            job_id=job_id, job_type=JobType.SYNC, db=test_async_session
        )

        # Update to running
        updated_job = await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.RUNNING,
            db=test_async_session,
            progress=25,
            message="Starting sync",
        )

        assert updated_job is not None
        assert updated_job.status == JobStatus.RUNNING.value
        assert updated_job.progress == 25
        assert updated_job.job_metadata["last_message"] == "Starting sync"
        assert updated_job.started_at is not None

        # Update to completed
        result_data = {"synced": 100, "errors": 0}
        completed_job = await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            db=test_async_session,
            progress=100,
            result=result_data,
        )

        assert completed_job is not None
        assert completed_job.status == JobStatus.COMPLETED.value
        assert completed_job.progress == 100
        assert completed_job.result == result_data
        assert completed_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_failed(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test updating job status to failed."""
        # Create a job
        job_id = "test-update-failed"
        await job_repository.create_job(
            job_id=job_id, job_type=JobType.ANALYSIS, db=test_async_session
        )

        # Update to failed
        error_msg = "Connection timeout"
        failed_job = await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            db=test_async_session,
            error=error_msg,
        )

        assert failed_job is not None
        assert failed_job.status == JobStatus.FAILED.value
        assert failed_job.error == error_msg
        assert failed_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_not_found(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test updating non-existent job."""
        updated = await job_repository.update_job_status(
            job_id="non-existent", status=JobStatus.RUNNING, db=test_async_session
        )
        assert updated is None

    @pytest.mark.asyncio
    async def test_cancel_job(self, test_async_session: AsyncSession) -> None:
        """Test cancelling a job."""
        # Create a running job
        job_id = "test-cancel"
        await job_repository.create_job(
            job_id=job_id, job_type=JobType.SYNC, db=test_async_session
        )
        await job_repository.update_job_status(
            job_id=job_id, status=JobStatus.RUNNING, db=test_async_session
        )

        # Cancel it
        cancelled_job = await job_repository.cancel_job(
            job_id=job_id, db=test_async_session
        )

        assert cancelled_job is not None
        assert cancelled_job.status == JobStatus.CANCELLED.value
        assert cancelled_job.completed_at is not None
        assert cancelled_job.job_metadata["last_message"] == "Job cancelled by user"

    @pytest.mark.asyncio
    async def test_list_jobs(self, test_async_session: AsyncSession) -> None:
        """Test listing jobs with filters."""
        # Create various jobs
        jobs_data = [
            ("job1", JobType.SYNC, JobStatus.PENDING),
            ("job2", JobType.SYNC, JobStatus.RUNNING),
            ("job3", JobType.ANALYSIS, JobStatus.COMPLETED),
            ("job4", JobType.ANALYSIS, JobStatus.FAILED),
            ("job5", JobType.CLEANUP, JobStatus.PENDING),
        ]

        for job_id, job_type, status in jobs_data:
            await job_repository.create_job(
                job_id=job_id, job_type=job_type, db=test_async_session
            )
            if status != JobStatus.PENDING:
                await job_repository.update_job_status(
                    job_id=job_id, status=status, db=test_async_session
                )

        # List all jobs
        all_jobs = await job_repository.list_jobs(db=test_async_session)
        assert len(all_jobs) >= 5

        # List by status
        pending_jobs = await job_repository.list_jobs(
            db=test_async_session, status=JobStatus.PENDING
        )
        assert len([j for j in pending_jobs if j.id in ["job1", "job5"]]) == 2

        # List by type
        sync_jobs = await job_repository.list_jobs(
            db=test_async_session, job_type=JobType.SYNC
        )
        assert len([j for j in sync_jobs if j.id in ["job1", "job2"]]) == 2

        # List with both filters
        pending_sync = await job_repository.list_jobs(
            db=test_async_session, status=JobStatus.PENDING, job_type=JobType.SYNC
        )
        assert len([j for j in pending_sync if j.id == "job1"]) == 1

        # Test pagination
        page1 = await job_repository.list_jobs(db=test_async_session, limit=2, offset=0)
        page2 = await job_repository.list_jobs(db=test_async_session, limit=2, offset=2)
        assert len(page1) <= 2
        assert all(p1.id != p2.id for p1 in page1 for p2 in page2)

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, test_async_session: AsyncSession) -> None:
        """Test getting active jobs."""
        # Create jobs with different statuses
        await job_repository.create_job(
            job_id="active1", job_type=JobType.SYNC, db=test_async_session
        )
        await job_repository.create_job(
            job_id="active2", job_type=JobType.ANALYSIS, db=test_async_session
        )
        await job_repository.update_job_status(
            job_id="active2", status=JobStatus.RUNNING, db=test_async_session
        )

        # Create completed job (should not be included)
        await job_repository.create_job(
            job_id="completed1", job_type=JobType.SYNC, db=test_async_session
        )
        await job_repository.update_job_status(
            job_id="completed1", status=JobStatus.COMPLETED, db=test_async_session
        )

        # Get all active jobs
        active_jobs = await job_repository.get_active_jobs(db=test_async_session)
        active_ids = [j.id for j in active_jobs]
        assert "active1" in active_ids
        assert "active2" in active_ids
        assert "completed1" not in active_ids

        # Get active jobs by type
        active_sync = await job_repository.get_active_jobs(
            db=test_async_session, job_type=JobType.SYNC
        )
        assert len([j for j in active_sync if j.id == "active1"]) == 1
        assert not any(j.id == "active2" for j in active_sync)

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(self, test_async_session: AsyncSession) -> None:
        """Test cleaning up old completed jobs."""
        # Create old completed job
        old_job = Job(
            id="old-job",
            type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            progress=100,
            completed_at=datetime.utcnow() - timedelta(days=35),
            created_at=datetime.utcnow() - timedelta(days=36),
            updated_at=datetime.utcnow() - timedelta(days=35),
        )
        test_async_session.add(old_job)

        # Create recent completed job
        recent_job = Job(
            id="recent-job",
            type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            progress=100,
            completed_at=datetime.utcnow() - timedelta(days=5),
            created_at=datetime.utcnow() - timedelta(days=6),
            updated_at=datetime.utcnow() - timedelta(days=5),
        )
        test_async_session.add(recent_job)

        # Create running job (should not be deleted)
        running_job = Job(
            id="running-job",
            type=JobType.SYNC.value,
            status=JobStatus.RUNNING.value,
            progress=50,
            started_at=datetime.utcnow() - timedelta(days=40),
            created_at=datetime.utcnow() - timedelta(days=40),
            updated_at=datetime.utcnow(),
        )
        test_async_session.add(running_job)

        await test_async_session.commit()

        # Clean up jobs older than 30 days
        deleted_count = await job_repository.cleanup_old_jobs(
            db=test_async_session, days=30
        )
        assert deleted_count == 1

        # Verify correct jobs remain
        remaining_jobs = await job_repository.list_jobs(
            db=test_async_session, limit=100
        )
        remaining_ids = [j.id for j in remaining_jobs]
        assert "old-job" not in remaining_ids
        assert "recent-job" in remaining_ids
        assert "running-job" in remaining_ids

    @pytest.mark.asyncio
    async def test_job_metadata_handling(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test job metadata operations."""
        job_id = "test-metadata"
        initial_metadata = {"key1": "value1", "key2": 123}

        # Create job with metadata
        job = await job_repository.create_job(
            job_id=job_id,
            job_type=JobType.ANALYSIS,
            db=test_async_session,
            metadata=initial_metadata,
        )
        assert job.job_metadata == initial_metadata

        # Update job with message (should merge with metadata)
        await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.RUNNING,
            db=test_async_session,
            message="Processing...",
        )

        updated_job = await job_repository.get_job(job_id=job_id, db=test_async_session)
        assert updated_job is not None
        assert updated_job.job_metadata["key1"] == "value1"
        assert updated_job.job_metadata["key2"] == 123
        assert updated_job.job_metadata["last_message"] == "Processing..."

    @pytest.mark.asyncio
    async def test_job_timestamps(self, test_async_session: AsyncSession) -> None:
        """Test job timestamp handling."""
        job_id = "test-timestamps"

        # Create job
        job = await job_repository.create_job(
            job_id=job_id, job_type=JobType.SYNC, db=test_async_session
        )
        assert job.created_at is not None
        assert job.started_at is None
        assert job.completed_at is None
        created_time = job.created_at

        # Start job
        await job_repository.update_job_status(
            job_id=job_id, status=JobStatus.RUNNING, db=test_async_session
        )
        job = await job_repository.get_job(job_id=job_id, db=test_async_session)
        assert job is not None
        assert job.started_at is not None
        assert job.completed_at is None
        assert job.updated_at > created_time

        # Complete job
        await job_repository.update_job_status(
            job_id=job_id, status=JobStatus.COMPLETED, db=test_async_session
        )
        job = await job_repository.get_job(job_id=job_id, db=test_async_session)
        assert job is not None
        assert job.completed_at is not None
        assert job.completed_at >= job.started_at

    @pytest.mark.asyncio
    async def test_edge_cases(self, test_async_session: AsyncSession) -> None:
        """Test edge cases and error conditions."""
        # Test creating job with empty metadata
        job1 = await job_repository.create_job(
            job_id="empty-metadata",
            job_type=JobType.SYNC,
            db=test_async_session,
            metadata={},
        )
        assert job1.job_metadata == {}

        # Test updating job with None values (should be ignored)
        await job_repository.update_job_status(
            job_id="empty-metadata",
            status=JobStatus.RUNNING,
            db=test_async_session,
            progress=None,
            result=None,
            error=None,
            message=None,
        )
        job = await job_repository.get_job(
            job_id="empty-metadata", db=test_async_session
        )
        assert job is not None
        assert job.progress == 0  # Should remain unchanged
        assert job.result is None
        assert job.error is None

        # Test multiple status updates
        job_id = "multi-update"
        await job_repository.create_job(
            job_id=job_id, job_type=JobType.ANALYSIS, db=test_async_session
        )

        # Should not update started_at twice
        await job_repository.update_job_status(
            job_id=job_id, status=JobStatus.RUNNING, db=test_async_session
        )
        job = await job_repository.get_job(job_id=job_id, db=test_async_session)
        first_started_at = job.started_at

        await job_repository.update_job_status(
            job_id=job_id, status=JobStatus.RUNNING, db=test_async_session, progress=50
        )
        job = await job_repository.get_job(job_id=job_id, db=test_async_session)
        assert job is not None
        assert job.started_at == first_started_at  # Should not change

    @pytest.mark.asyncio
    async def test_job_type_enum_values(self, test_async_session: AsyncSession) -> None:
        """Test all job type enum values work correctly."""
        job_types = list(JobType)

        for i, job_type in enumerate(job_types):
            job_id = f"job-type-{job_type.value}"
            job = await job_repository.create_job(
                job_id=job_id, job_type=job_type, db=test_async_session
            )
            assert job.type == job_type.value

        # Verify we can filter by each type
        for job_type in job_types:
            jobs = await job_repository.list_jobs(
                db=test_async_session, job_type=job_type, limit=100
            )
            assert any(j.id == f"job-type-{job_type.value}" for j in jobs)
