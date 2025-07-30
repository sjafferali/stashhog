"""Stash scan jobs for metadata scanning."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from app.core.settings_loader import load_settings_with_db_overrides
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)

# GraphQL mutations
METADATA_SCAN_MUTATION = """
mutation MetadataScan($input: ScanMetadataInput!) {
    metadataScan(input: $input)
}
"""

STOP_JOB_MUTATION = """
mutation StopJob($job_id: ID!) {
    stopJob(job_id: $job_id)
}
"""

# GraphQL queries
JOB_STATUS_QUERY = """
query FindJob($input: FindJobInput!) {
    findJob(input: $input) {
        id
        status
        progress
        description
        startTime
        endTime
        error
    }
}
"""

JOB_QUEUE_QUERY = """
query JobQueue {
    jobQueue {
        id
        status
        progress
        description
        startTime
        endTime
        error
    }
}
"""


# _handle_cancellation function removed - cancellation is now handled inline in _poll_job_status


async def _update_progress_if_changed(
    progress: float,
    last_progress: float,
    description: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> float:
    """Update progress if it has changed."""
    if progress != last_progress:
        progress_int = int(progress * 100) if progress else 0
        await progress_callback(progress_int, f"Stash scan: {description}")
        return progress
    return last_progress


def _process_job_status(
    job: Dict[str, Any], stash_job_id: str
) -> Optional[Dict[str, Any]]:
    """Process job status and return result if terminal state."""
    status = job.get("status", "").upper()

    if status == "FINISHED":
        return {
            "status": "completed",
            "message": "Stash scan completed successfully",
            "stash_job_id": stash_job_id,
            "start_time": job.get("startTime"),
            "end_time": job.get("endTime"),
        }
    elif status == "FAILED":
        return {
            "status": "failed",
            "error": job.get("error") or "Stash scan failed",
            "stash_job_id": stash_job_id,
        }
    elif status == "CANCELLED":
        return {
            "status": "cancelled",
            "message": "Stash scan was cancelled",
            "stash_job_id": stash_job_id,
        }
    elif status == "STOPPING":
        logger.info(f"Stash job {stash_job_id} is stopping...")

    return None


async def _poll_job_status(
    stash_service: Any,
    stash_job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
) -> Dict[str, Any]:
    """Poll Stash job status until completion."""
    last_progress: float = 0
    poll_interval = 2  # seconds
    cancellation_requested = False

    while True:
        # If cancellation is requested but not yet sent to Stash
        if (
            cancellation_token
            and cancellation_token.is_cancelled
            and not cancellation_requested
        ):
            logger.info(f"Cancellation requested for Stash job {stash_job_id}")
            try:
                await stash_service.execute_graphql(
                    STOP_JOB_MUTATION, {"job_id": stash_job_id}
                )
                cancellation_requested = True
                logger.info(
                    f"Sent cancellation request to Stash for job {stash_job_id}"
                )
            except Exception as e:
                logger.error(f"Failed to stop Stash job {stash_job_id}: {e}")
                # Even if the stop request fails, mark as requested to avoid retrying
                cancellation_requested = True

        try:
            result = await stash_service.execute_graphql(
                JOB_STATUS_QUERY, {"input": {"id": stash_job_id}}
            )

            job = result.get("findJob")
            if not job:
                logger.error(f"Job {stash_job_id} not found in Stash")
                return {
                    "status": "failed",
                    "error": f"Job {stash_job_id} not found in Stash",
                    "stash_job_id": stash_job_id,
                }

            progress = job.get("progress", 0)
            description = job.get("description", "")

            last_progress = await _update_progress_if_changed(
                progress, last_progress, description, progress_callback
            )

            job_result = _process_job_status(job, stash_job_id)
            if job_result:
                return job_result

            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error polling job status: {e}")
            await asyncio.sleep(poll_interval)


async def stash_scan_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute a Stash metadata scan job."""
    logger.info(f"Starting Stash scan job {job_id}")

    try:
        # Initial progress
        await progress_callback(0, "Starting Stash metadata scan")

        # Initialize services following the pattern from sync_jobs
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )

        # Prepare scan input with provided settings
        scan_input = {
            "paths": ["/data"],  # Default path as specified
            "rescan": kwargs.get("rescan", False),
            "scanGenerateCovers": kwargs.get("scanGenerateCovers", True),
            "scanGeneratePreviews": kwargs.get("scanGeneratePreviews", True),
            "scanGenerateImagePreviews": kwargs.get("scanGenerateImagePreviews", False),
            "scanGenerateSprites": kwargs.get("scanGenerateSprites", True),
            "scanGeneratePhashes": kwargs.get("scanGeneratePhashes", True),
            "scanGenerateThumbnails": kwargs.get("scanGenerateThumbnails", False),
            "scanGenerateClipPreviews": kwargs.get("scanGenerateClipPreviews", False),
        }

        # Allow override of paths if provided
        if "paths" in kwargs:
            scan_input["paths"] = kwargs["paths"]

        logger.info(f"Starting metadata scan with input: {scan_input}")
        await progress_callback(5, "Triggering metadata scan in Stash")

        # Execute metadata scan mutation
        result = await stash_service.execute_graphql(
            METADATA_SCAN_MUTATION, {"input": scan_input}
        )

        stash_job_id = result.get("metadataScan")
        if not stash_job_id:
            raise Exception("Failed to start metadata scan - no job ID returned")

        logger.info(f"Started Stash job {stash_job_id}")
        await progress_callback(10, f"Stash job started: {stash_job_id}")

        # Poll job status until completion
        poll_result = await _poll_job_status(
            stash_service, stash_job_id, progress_callback, cancellation_token
        )

        # Final progress
        final_status = poll_result.get("status", "completed")
        if final_status == "completed":
            await progress_callback(100, "Stash metadata scan completed")
        elif final_status == "cancelled":
            await progress_callback(100, "Stash metadata scan cancelled")
        else:
            await progress_callback(100, f"Stash metadata scan {final_status}")

        return {"job_id": job_id, "stash_job_id": stash_job_id, **poll_result}

    except Exception as e:
        error_msg = f"Stash scan job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Don't update progress in error handler - let job service handle it
        raise
    finally:
        # Close Stash service connection
        if "stash_service" in locals():
            await stash_service.close()


def register_stash_scan_jobs(job_service: JobService) -> None:
    """Register Stash scan job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.STASH_SCAN, stash_scan_job)

    logger.info("Registered Stash scan job handlers")
