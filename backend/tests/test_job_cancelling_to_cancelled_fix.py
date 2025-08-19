"""Test that CANCELLING status jobs appear in active jobs, not historical."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import job_repository


@pytest.mark.asyncio
async def test_cancelling_job_appears_in_active_jobs(test_async_session: AsyncSession):
    """Test that jobs with CANCELLING status appear in active jobs."""
    # Create jobs with different statuses
    jobs = [
        Job(
            id="pending-job",
            type=JobType.SYNC.value,
            status=JobStatus.PENDING.value,
            progress=0,
        ),
        Job(
            id="running-job",
            type=JobType.SYNC.value,
            status=JobStatus.RUNNING.value,
            progress=50,
        ),
        Job(
            id="cancelling-job",
            type=JobType.SYNC.value,
            status=JobStatus.CANCELLING.value,
            progress=75,
        ),
        Job(
            id="completed-job",
            type=JobType.SYNC.value,
            status=JobStatus.COMPLETED.value,
            progress=100,
        ),
        Job(
            id="failed-job",
            type=JobType.SYNC.value,
            status=JobStatus.FAILED.value,
            progress=30,
        ),
        Job(
            id="cancelled-job",
            type=JobType.SYNC.value,
            status=JobStatus.CANCELLED.value,
            progress=60,
        ),
    ]

    for job in jobs:
        test_async_session.add(job)
    await test_async_session.commit()

    # Get active jobs
    active_jobs = await job_repository.get_active_jobs(test_async_session)
    active_job_ids = {job.id for job in active_jobs}

    # Check that CANCELLING is in active jobs
    assert "cancelling-job" in active_job_ids, "CANCELLING job should be in active jobs"
    assert "pending-job" in active_job_ids, "PENDING job should be in active jobs"
    assert "running-job" in active_job_ids, "RUNNING job should be in active jobs"

    # Check that completed/failed/cancelled are NOT in active jobs
    assert (
        "completed-job" not in active_job_ids
    ), "COMPLETED job should NOT be in active jobs"
    assert "failed-job" not in active_job_ids, "FAILED job should NOT be in active jobs"
    assert (
        "cancelled-job" not in active_job_ids
    ), "CANCELLED job should NOT be in active jobs"

    # Active jobs should be exactly 3 (pending, running, cancelling)
    assert len(active_jobs) == 3, f"Expected 3 active jobs, got {len(active_jobs)}"


@pytest.mark.asyncio
async def test_api_endpoints_correctly_filter_cancelling_jobs(
    test_async_session: AsyncSession,
):
    """Test that API endpoints correctly categorize CANCELLING jobs."""
    from app.api.routes.jobs import get_active_jobs_endpoint, list_jobs
    from app.services.job_service import JobService

    # Create a cancelling job
    cancelling_job = Job(
        id="test-cancelling-job",
        type=JobType.SYNC.value,
        status=JobStatus.CANCELLING.value,
        progress=50,
    )
    test_async_session.add(cancelling_job)

    # Create a completed job
    completed_job = Job(
        id="test-completed-job",
        type=JobType.SYNC.value,
        status=JobStatus.COMPLETED.value,
        progress=100,
    )
    test_async_session.add(completed_job)
    await test_async_session.commit()

    # Create job service
    job_service = JobService()

    # Test active jobs endpoint
    active_response = await get_active_jobs_endpoint(
        job_type=None, job_service=job_service, db=test_async_session
    )

    active_job_ids = {job.id for job in active_response.jobs}
    assert (
        "test-cancelling-job" in active_job_ids
    ), "CANCELLING job should be in active jobs"
    assert (
        "test-completed-job" not in active_job_ids
    ), "COMPLETED job should NOT be in active jobs"

    # Test historical jobs endpoint
    historical_response = await list_jobs(
        status=None,
        job_type=None,
        job_id=None,
        limit=100,
        offset=0,
        db=test_async_session,
        job_service=job_service,
    )

    historical_job_ids = {job.id for job in historical_response.jobs}
    assert (
        "test-cancelling-job" not in historical_job_ids
    ), "CANCELLING job should NOT be in historical jobs"
    assert (
        "test-completed-job" in historical_job_ids
    ), "COMPLETED job should be in historical jobs"
