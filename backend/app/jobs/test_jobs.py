"""Test job implementation for daemon testing."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

from app.core.cancellation import CancellationToken
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


async def test_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[CancellationToken] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Test job that simulates work and demonstrates progress updates.

    This job is used by the TestDaemon to demonstrate job orchestration.
    Follows the standard job patterns to avoid greenlet errors.
    """
    logger.info(f"Starting test job {job_id}")

    try:
        # Initial progress
        await progress_callback(0, "Test job starting...")

        # Get job metadata
        iteration = kwargs.get("iteration", 0)
        daemon_id = kwargs.get("daemon_id", "unknown")

        # Simulate work with progress updates
        total_steps = 5
        processed_steps = 0

        for step in range(total_steps):
            # Check cancellation
            if cancellation_token and cancellation_token.is_cancelled:
                logger.info(f"Test job {job_id} was cancelled")
                return {
                    "job_id": job_id,
                    "status": "cancelled",
                    "total_items": total_steps,
                    "processed_items": processed_steps,
                }

            # Simulate work
            await asyncio.sleep(2)

            # Update counts
            processed_steps = step + 1

            # Calculate progress percentage
            progress = int((processed_steps / total_steps) * 100)

            # Update progress with standard message format for automatic parsing
            message = f"Processed {processed_steps}/{total_steps} test steps"
            await progress_callback(progress, message)

            logger.info(
                f"Test job {job_id}: Step {processed_steps} completed (iteration {iteration})"
            )

        # Final progress update
        await progress_callback(100, "Test job completed")

        # Return standard result format
        result = {
            "job_id": job_id,
            "status": "completed",
            "total_items": total_steps,
            "processed_items": processed_steps,
            "iteration": iteration,
            "daemon_id": daemon_id,
            "message": f"Test job completed successfully for iteration {iteration}",
        }

        logger.info(f"Test job {job_id} completed successfully")
        return result

    except asyncio.CancelledError:
        # Handle cancellation properly
        logger.info(f"Test job {job_id} was cancelled")
        return {
            "job_id": job_id,
            "status": "cancelled",
            "total_items": total_steps if "total_steps" in locals() else 0,
            "processed_items": processed_steps if "processed_steps" in locals() else 0,
        }
    except Exception as e:
        error_msg = f"Test job failed: {str(e)}"
        logger.error(f"Test job {job_id} failed: {str(e)}", exc_info=True)
        # Don't call progress_callback in error handler - let job service handle it
        raise


def register_test_job_handlers(job_service: JobService) -> None:
    """Register test job handlers with the job service."""
    job_service.register_handler(JobType.TEST, test_job)
    logger.info("Registered test job handler")
