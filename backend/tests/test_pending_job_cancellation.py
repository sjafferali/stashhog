"""Tests for cancelling pending jobs."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cancellation import CancellationToken
from app.jobs.analysis_jobs import analyze_scenes_job
from app.models.job import JobStatus, JobType
from app.repositories.job_repository import job_repository
from app.services.job_service import JobService


@pytest.mark.asyncio
async def test_cancel_pending_job(test_async_session: AsyncSession):
    """Test cancelling a job in pending status."""
    # Create a pending job
    job = await job_repository.create_job(
        job_id="test-pending-job",
        job_type=JobType.ANALYSIS,
        db=test_async_session,
        metadata={"scene_ids": ["scene1", "scene2"]},
    )
    await test_async_session.commit()

    # Verify job is pending
    assert job.status == JobStatus.PENDING

    # Create job service and mock the _send_job_update method
    job_service = JobService()
    with patch.object(job_service, "_send_job_update", new_callable=AsyncMock):
        # Cancel the pending job
        success = await job_service.cancel_job("test-pending-job", test_async_session)
        assert success is True

    # Verify job status changed to CANCELLED
    cancelled_job = await job_repository.get_job("test-pending-job", test_async_session)
    assert cancelled_job is not None
    assert cancelled_job.status == JobStatus.CANCELLED
    assert cancelled_job.error == "Cancelled by user"
    assert cancelled_job.completed_at is not None


@pytest.mark.asyncio
async def test_cancel_pending_vs_running_job(test_async_session: AsyncSession):
    """Test different behavior for cancelling pending vs running jobs."""
    # Create a pending job
    await job_repository.create_job(
        job_id="test-pending",
        job_type=JobType.ANALYSIS,
        db=test_async_session,
    )

    # Create a running job
    running_job = await job_repository.create_job(
        job_id="test-running",
        job_type=JobType.SYNC_SCENES,
        db=test_async_session,
    )
    running_job.mark_started()
    await test_async_session.commit()

    job_service = JobService()

    with patch.object(job_service, "_send_job_update", new_callable=AsyncMock):
        # Cancel pending job - should go straight to CANCELLED
        await job_service.cancel_job("test-pending", test_async_session)
        pending_result = await job_repository.get_job(
            "test-pending", test_async_session
        )
        assert pending_result.status == JobStatus.CANCELLED

        # Cancel running job - should go to CANCELLING first
        await job_service.cancel_job("test-running", test_async_session)
        running_result = await job_repository.get_job(
            "test-running", test_async_session
        )
        assert running_result.status == JobStatus.CANCELLING


@pytest.mark.asyncio
async def test_analyze_scenes_job_cancelled_before_start():
    """Test that analysis job exits immediately if cancelled before starting."""
    # Create a pre-cancelled token
    cancelled_token = CancellationToken()
    cancelled_token.cancel()

    # Create mock progress callback
    progress_callback = AsyncMock()

    # Try to run the job with cancelled token
    with pytest.raises(asyncio.CancelledError):
        await analyze_scenes_job(
            job_id="test-job",
            progress_callback=progress_callback,
            cancellation_token=cancelled_token,
            scene_ids=["scene1", "scene2"],
        )

    # Verify no progress was reported
    progress_callback.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_pending_job_with_task_id(test_async_session: AsyncSession):
    """Test cancelling a pending job that has a queued task."""
    # Create a pending job with task_id in metadata
    await job_repository.create_job(
        job_id="test-pending-task",
        job_type=JobType.ANALYSIS,
        db=test_async_session,
        metadata={"task_id": "task-123"},
    )
    await test_async_session.commit()

    job_service = JobService()

    # Mock the task queue and _send_job_update
    with (
        patch("app.services.job_service.get_task_queue") as mock_get_queue,
        patch.object(job_service, "_send_job_update", new_callable=AsyncMock),
    ):
        mock_queue = Mock()
        mock_queue.cancel_task = AsyncMock()
        mock_get_queue.return_value = mock_queue

        # Cancel the job
        success = await job_service.cancel_job("test-pending-task", test_async_session)
        assert success is True

        # Verify task was cancelled
        mock_queue.cancel_task.assert_called_once_with("task-123")

    # Verify job status
    cancelled_job = await job_repository.get_job(
        "test-pending-task", test_async_session
    )
    assert cancelled_job.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_non_cancellable_job(test_async_session: AsyncSession):
    """Test that completed/failed jobs cannot be cancelled."""
    # Create a completed job
    completed_job = await job_repository.create_job(
        job_id="test-completed",
        job_type=JobType.ANALYSIS,
        db=test_async_session,
    )
    completed_job.mark_completed({"result": "success"})
    await test_async_session.commit()

    # Verify job cannot be cancelled
    assert not completed_job.can_be_cancelled()

    # Create a failed job
    failed_job = await job_repository.create_job(
        job_id="test-failed",
        job_type=JobType.ANALYSIS,
        db=test_async_session,
    )
    failed_job.mark_failed("Test error")
    await test_async_session.commit()

    # Verify job cannot be cancelled
    assert not failed_job.can_be_cancelled()


@pytest.mark.asyncio
async def test_multiple_pending_job_types(test_async_session: AsyncSession):
    """Test cancelling different types of pending jobs."""
    job_service = JobService()

    # Create various pending job types
    job_types = [
        JobType.ANALYSIS,
        JobType.SYNC_SCENES,
        JobType.APPLY_PLAN,
        JobType.GENERATE_DETAILS,
    ]

    jobs = []
    for i, job_type in enumerate(job_types):
        job = await job_repository.create_job(
            job_id=f"test-{job_type.value}-{i}",
            job_type=job_type,
            db=test_async_session,
        )
        jobs.append(job)

    await test_async_session.commit()

    # Cancel all jobs with mocked _send_job_update
    with patch.object(job_service, "_send_job_update", new_callable=AsyncMock):
        for job in jobs:
            success = await job_service.cancel_job(job.id, test_async_session)
            assert success is True

            # Verify cancellation
            cancelled = await job_repository.get_job(job.id, test_async_session)
            assert cancelled.status == JobStatus.CANCELLED
            assert cancelled.error == "Cancelled by user"
