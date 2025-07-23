import logging
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional

from sqlalchemy import and_, select

from app.core.database import AsyncSessionLocal
from app.core.tasks import TaskStatus, get_task_queue
from app.models.job import Job, JobStatus, JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

# Timeout threshold for jobs that should have completed
JOB_TIMEOUT_MINUTES = {
    JobType.SYNC: 30,
    JobType.SYNC_ALL: 30,
    JobType.SYNC_SCENES: 30,
    JobType.SYNC_PERFORMERS: 20,
    JobType.SYNC_TAGS: 20,
    JobType.SYNC_STUDIOS: 20,
    JobType.ANALYSIS: 60,  # AI analysis can take longer
    JobType.APPLY_PLAN: 30,
    JobType.GENERATE_DETAILS: 45,
    JobType.EXPORT: 15,
    JobType.IMPORT: 15,
    JobType.CLEANUP: 5,
}

# Default timeout for unknown job types
DEFAULT_TIMEOUT_MINUTES = 30


async def _cleanup_old_jobs(db: Any, current_time: datetime) -> int:
    """Delete old completed jobs (older than 30 days)."""
    old_job_cutoff = current_time - timedelta(days=30)
    old_jobs_query = select(Job).where(
        and_(
            Job.status.in_(
                [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            ),
            Job.completed_at < old_job_cutoff,
        )
    )
    old_jobs_result = await db.execute(old_jobs_query)
    old_jobs = old_jobs_result.scalars().all()

    old_jobs_deleted = 0
    for old_job in old_jobs:
        try:
            await db.delete(old_job)
            old_jobs_deleted += 1
        except Exception as e:
            logger.error(f"Error deleting old job {old_job.id}: {str(e)}")

    if old_jobs_deleted > 0:
        await db.commit()
        logger.info(f"Deleted {old_jobs_deleted} old completed jobs")

    return old_jobs_deleted


async def _process_stale_job(
    job: Job,
    current_time: datetime,
    task_queue: Any,
) -> Optional[Dict[str, Any]]:
    """Process a single potentially stale job."""
    # Determine timeout for this job type
    job_type = job.type if isinstance(job.type, JobType) else JobType(job.type)
    timeout_minutes = JOB_TIMEOUT_MINUTES.get(job_type, DEFAULT_TIMEOUT_MINUTES)

    # Check if job has exceeded timeout
    job_start_time = job.started_at or job.created_at
    time_elapsed = current_time - job_start_time

    if time_elapsed <= timedelta(minutes=timeout_minutes):
        return None

    # Job has exceeded timeout
    logger.warning(
        f"Job {job.id} ({job_type.value}) has exceeded timeout "
        f"({time_elapsed.total_seconds() / 60:.1f} minutes > {timeout_minutes} minutes)"
    )

    # Check if the task is actually running
    task_id = None
    if job.job_metadata and isinstance(job.job_metadata, dict):
        task_id = job.job_metadata.get("task_id")

    is_actually_running = False
    if task_id:
        task = task_queue.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            is_actually_running = True
            logger.info(f"Job {job.id} task {task_id} is still running")

    if is_actually_running:
        return None

    # Job is not actually running, mark it as failed
    job.status = JobStatus.FAILED  # type: ignore[assignment]
    job.error = f"Job timed out after {time_elapsed.total_seconds() / 60:.1f} minutes"  # type: ignore[assignment]
    job.completed_at = current_time  # type: ignore[assignment]

    # Check if job completed but didn't update status
    if job.progress == 100:
        job.status = JobStatus.COMPLETED  # type: ignore[assignment]
        job.error = None  # type: ignore[assignment]
        logger.info(f"Job {job.id} was actually completed but status wasn't updated")

    logger.info(
        f"Marked job {job.id} as {job.status.value if hasattr(job.status, 'value') else job.status}"
    )

    return {
        "job_id": job.id,
        "job_type": job_type.value,
        "status": job.status.value if hasattr(job.status, "value") else job.status,
        "timeout_minutes": timeout_minutes,
        "elapsed_minutes": time_elapsed.total_seconds() / 60,
    }


async def cleanup_stale_jobs(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Cleanup stale jobs that are marked as running but have exceeded their timeout.

    This job will:
    1. Find all jobs marked as RUNNING or PENDING
    2. Check if they have exceeded their timeout threshold
    3. Check if the associated task is actually running
    4. Update the job status accordingly
    """
    logger.info(f"Starting cleanup job {job_id}")

    cleaned_jobs = []
    errors = []

    async with AsyncSessionLocal() as db:
        try:
            # Progress: Starting cleanup
            await progress_callback(10, "Finding stale jobs...")

            # Find all jobs that are marked as running or pending
            current_time = datetime.utcnow()
            query = select(Job).where(
                Job.status.in_([JobStatus.RUNNING, JobStatus.PENDING])
            )
            result = await db.execute(query)
            potentially_stale_jobs = result.scalars().all()

            total_jobs = len(potentially_stale_jobs)
            logger.info(f"Found {total_jobs} potentially stale jobs")

            if total_jobs == 0:
                await progress_callback(100, "No stale jobs found")
                return {"status": "completed", "cleaned_jobs": 0, "errors": []}

            # Progress: Processing jobs
            await progress_callback(20, f"Processing {total_jobs} jobs...")

            task_queue = get_task_queue()

            for idx, job in enumerate(potentially_stale_jobs):
                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("Cleanup job cancelled")
                    break

                # Calculate progress
                progress = 20 + int((idx / total_jobs) * 70)
                await progress_callback(
                    progress,
                    f"Checking job {job.id} ({job.type.value if hasattr(job.type, 'value') else job.type})",
                )

                try:
                    job_result = await _process_stale_job(job, current_time, task_queue)
                    if job_result:
                        cleaned_jobs.append(job_result)

                except Exception as e:
                    logger.error(f"Error processing job {job.id}: {str(e)}")
                    errors.append({"job_id": job.id, "error": str(e)})

            # Commit all changes
            await db.commit()

            # Progress: Completing
            await progress_callback(90, "Finalizing cleanup...")

            # Cleanup old completed jobs
            old_jobs_deleted = await _cleanup_old_jobs(db, current_time)

            await progress_callback(100, "Cleanup completed")

            return {
                "status": "completed",
                "cleaned_jobs": len(cleaned_jobs),
                "cleaned_job_details": cleaned_jobs,
                "old_jobs_deleted": old_jobs_deleted,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Cleanup job failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "cleaned_jobs": len(cleaned_jobs),
                "errors": errors,
            }


def register_cleanup_jobs(job_service: JobService) -> None:
    """Register cleanup job handlers.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.CLEANUP, cleanup_stale_jobs)
    logger.info("Registered cleanup job handlers")
