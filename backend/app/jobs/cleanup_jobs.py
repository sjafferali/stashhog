import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.tasks import TaskStatus, get_task_queue
from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.handled_download import HandledDownload
from app.models.job import Job, JobStatus, JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

# Timeout threshold for jobs that should have completed
JOB_TIMEOUT_MINUTES = {
    # Full sync from Stash (all entities - scenes, performers, tags, studios)
    JobType.SYNC: 30,
    # Sync specific scenes from Stash
    JobType.SYNC_SCENES: 30,
    # AI-powered scene analysis using OpenAI Vision API
    JobType.ANALYSIS: 60,  # AI analysis can take longer
    # Apply analysis plan to update Stash with generated tags/details
    JobType.APPLY_PLAN: 30,
    # Generate scene details using AI (handler exists but no API endpoint)
    JobType.GENERATE_DETAILS: 45,
    # Export functionality (not implemented - no handler or endpoints)
    # TODO: Consider removing if not planned for implementation
    JobType.EXPORT: 15,
    # Import functionality (not implemented - no handler or endpoints)
    # TODO: Consider removing if not planned for implementation
    JobType.IMPORT: 15,
    # Cleanup stale jobs and stuck pending plans
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


async def _cleanup_old_handled_downloads(db: Any, current_time: datetime) -> int:
    """Delete old handled_downloads entries (older than 14 days)."""
    old_download_cutoff = current_time - timedelta(days=14)
    old_downloads_query = select(HandledDownload).where(
        HandledDownload.timestamp < old_download_cutoff
    )
    old_downloads_result = await db.execute(old_downloads_query)
    old_downloads = old_downloads_result.scalars().all()

    old_downloads_deleted = 0
    for old_download in old_downloads:
        try:
            await db.delete(old_download)
            old_downloads_deleted += 1
        except Exception as e:
            logger.error(
                f"Error deleting old handled_download {old_download.id}: {str(e)}"
            )

    if old_downloads_deleted > 0:
        await db.commit()
        logger.info(f"Deleted {old_downloads_deleted} old handled_downloads entries")

    return old_downloads_deleted


async def _cleanup_stuck_pending_plans(
    db: Any, current_time: datetime
) -> Tuple[int, Optional[str]]:
    """Find and update plans stuck in PENDING state whose associated job is no longer running."""
    try:
        # Find all plans in PENDING status
        pending_plans_query = select(AnalysisPlan).where(
            AnalysisPlan.status == PlanStatus.PENDING
        )
        pending_plans_result = await db.execute(pending_plans_query)
        pending_plans = pending_plans_result.scalars().all()

        plans_updated = 0

        for plan in pending_plans:
            # Skip if no job_id associated
            if not plan.job_id:
                logger.warning(
                    f"Plan {plan.id} is PENDING but has no associated job_id"
                )
                # Set to DRAFT anyway since it's orphaned
                plan.status = PlanStatus.DRAFT
                plans_updated += 1
                continue

            # Check if the associated job exists and its status
            job_query = select(Job).where(Job.id == plan.job_id)
            job_result = await db.execute(job_query)
            job = job_result.scalar_one_or_none()

            if not job:
                # Job doesn't exist, set plan to DRAFT
                logger.warning(
                    f"Plan {plan.id} references non-existent job {plan.job_id}"
                )
                plan.status = PlanStatus.DRAFT
                plans_updated += 1
            elif job.status not in [JobStatus.RUNNING, JobStatus.PENDING]:
                # Job is no longer running, set plan to DRAFT
                logger.info(
                    f"Plan {plan.id} is PENDING but job {job.id} has status {job.status.value if hasattr(job.status, 'value') else job.status}"
                )
                plan.status = PlanStatus.DRAFT
                plans_updated += 1

        if plans_updated > 0:
            await db.commit()
            logger.info(f"Updated {plans_updated} stuck PENDING plans to DRAFT status")

        return plans_updated, None

    except Exception as e:
        logger.error(f"Error cleaning up stuck pending plans: {str(e)}")
        return 0, str(e)


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


async def _find_stale_jobs(db: AsyncSession) -> list[Job]:
    """Find all jobs that are marked as running or pending."""
    query = select(Job).where(Job.status.in_([JobStatus.RUNNING, JobStatus.PENDING]))
    result = await db.execute(query)
    return list(result.scalars().all())


async def _process_stale_jobs(
    jobs: list[Job],
    current_time: datetime,
    task_queue: Any,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
) -> tuple[list[dict], list[dict]]:
    """Process potentially stale jobs and return cleaned jobs and errors."""
    cleaned_jobs = []
    errors = []
    total_jobs = len(jobs)

    for idx, job in enumerate(jobs):
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

    return cleaned_jobs, errors


async def _finalize_cleanup(
    db: AsyncSession,
    current_time: datetime,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> tuple[int, int, int, Optional[str]]:
    """Finalize cleanup by deleting old jobs, handled downloads, and updating stuck plans."""
    await progress_callback(90, "Finalizing cleanup...")

    # Cleanup old completed jobs
    old_jobs_deleted = await _cleanup_old_jobs(db, current_time)

    # Cleanup old handled_downloads entries
    await progress_callback(92, "Cleaning up old download logs...")
    old_downloads_deleted = await _cleanup_old_handled_downloads(db, current_time)

    # Progress: Cleaning up stuck pending plans
    await progress_callback(95, "Cleaning up stuck pending plans...")
    stuck_plans_updated, stuck_plans_error = await _cleanup_stuck_pending_plans(
        db, current_time
    )

    return (
        old_jobs_deleted,
        old_downloads_deleted,
        stuck_plans_updated,
        stuck_plans_error,
    )


async def cleanup_stale_jobs(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Cleanup stale jobs that are marked as running but have exceeded their timeout,
    cleanup stuck pending plans, and purge old download logs.

    This job will:
    1. Find all jobs marked as RUNNING or PENDING
    2. Check if they have exceeded their timeout threshold
    3. Check if the associated task is actually running
    4. Update the job status accordingly
    5. Delete old completed jobs (older than 30 days)
    6. Delete old handled_downloads entries (older than 14 days)
    7. Find plans stuck in PENDING status where the associated job is no longer running
    8. Update stuck PENDING plans to DRAFT status
    """
    logger.info(f"Starting cleanup job {job_id}")

    async with AsyncSessionLocal() as db:
        try:
            # Progress: Starting cleanup
            await progress_callback(10, "Finding stale jobs...")

            current_time = datetime.now(timezone.utc)
            potentially_stale_jobs = await _find_stale_jobs(db)

            total_jobs = len(potentially_stale_jobs)
            logger.info(f"Found {total_jobs} potentially stale jobs")

            if total_jobs == 0:
                await progress_callback(100, "No stale jobs found")
                return {"status": "completed", "cleaned_jobs": 0, "errors": []}

            # Progress: Processing jobs
            await progress_callback(20, f"Processing {total_jobs} jobs...")

            task_queue = get_task_queue()
            cleaned_jobs, errors = await _process_stale_jobs(
                potentially_stale_jobs,
                current_time,
                task_queue,
                progress_callback,
                cancellation_token,
            )

            # Commit all changes
            await db.commit()

            # Finalize cleanup
            (
                old_jobs_deleted,
                old_downloads_deleted,
                stuck_plans_updated,
                stuck_plans_error,
            ) = await _finalize_cleanup(db, current_time, progress_callback)

            if stuck_plans_error:
                errors.append(
                    {
                        "error": f"Failed to cleanup stuck pending plans: {stuck_plans_error}"
                    }
                )

            await progress_callback(100, "Cleanup completed")

            return {
                "cleaned_jobs": len(cleaned_jobs),
                "cleaned_job_details": cleaned_jobs,
                "old_jobs_deleted": old_jobs_deleted,
                "old_downloads_deleted": old_downloads_deleted,
                "stuck_plans_updated": stuck_plans_updated,
                "errors": errors,
                "status": "completed_with_errors" if errors else "completed",
            }

        except Exception as e:
            logger.error(f"Cleanup job failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "cleaned_jobs": 0,
                "errors": [],
            }


def register_cleanup_jobs(job_service: JobService) -> None:
    """Register cleanup job handlers.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.CLEANUP, cleanup_stale_jobs)
    logger.info("Registered cleanup job handlers")
