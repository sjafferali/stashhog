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
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: CancellationToken,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Test job that simulates work and demonstrates progress updates.

    This job is used by the TestDaemon to demonstrate job orchestration.
    """
    try:
        logger.info(f"Starting test job {job_id}")
        await progress_callback(0, "Test job starting...")

        # Get job metadata
        iteration = kwargs.get("iteration", 0)
        daemon_id = kwargs.get("daemon_id", "unknown")

        # Simulate work with progress updates
        total_steps = 5
        for step in range(total_steps):
            if cancellation_token.is_cancelled:
                logger.info(f"Test job {job_id} was cancelled")
                return {"status": "cancelled", "completed_steps": step}

            # Simulate work
            await asyncio.sleep(2)

            # Update progress
            progress = int((step + 1) / total_steps * 100)
            message = (
                f"Test step {step + 1}/{total_steps} - Processing iteration {iteration}"
            )
            await progress_callback(progress, message)

            logger.info(f"Test job {job_id}: {message}")

        # Job completed successfully
        result = {
            "status": "completed",
            "iteration": iteration,
            "daemon_id": daemon_id,
            "message": f"Test job completed successfully for iteration {iteration}",
            "steps_completed": total_steps,
        }

        logger.info(f"Test job {job_id} completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Test job {job_id} failed: {str(e)}")
        raise


def register_test_job_handlers(job_service: JobService) -> None:
    """Register test job handlers with the job service."""
    job_service.register_handler(JobType.TEST, test_job)
    logger.info("Registered test job handler")
