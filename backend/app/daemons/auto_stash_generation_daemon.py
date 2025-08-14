"""Auto Stash Generation Daemon - automatically generates resources in Stash."""

import asyncio
import time
import traceback
from typing import Optional, Set

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.daemons.base import BaseDaemon
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType


class AutoStashGenerationDaemon(BaseDaemon):
    """
    Daemon that automatically generates resources in Stash when needed.

    This daemon:
    1. Checks for running jobs and waits if any are active
    2. Runs a Check Stash Generation Status job to see if generation is needed
    3. Runs a Stash metadata generate job if needed
    4. Sleeps for a configured interval before repeating

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between generation checks (default: 3600)
        retry_interval_seconds (int): Seconds to wait when jobs are running (default: 3600)
    """

    daemon_type = DaemonType.AUTO_STASH_GENERATION_DAEMON

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        self._current_job_id: Optional[str] = None
        self._waiting_for_jobs = False
        await self.log(LogLevel.INFO, "Auto Stash Generation Daemon initialized")

    async def on_stop(self) -> None:
        """Clean up daemon-specific resources."""
        await self.log(
            LogLevel.INFO,
            f"Auto Stash Generation Daemon shutting down. "
            f"Uptime: {self.get_uptime_seconds():.1f} seconds",
        )
        await super().on_stop()

    async def run(self):
        """Main daemon execution loop."""
        config = self._load_config()
        await self.log(
            LogLevel.INFO, f"Auto Stash Generation Daemon started with config: {config}"
        )

        state = {"last_heartbeat_time": 0}

        while self.is_running:
            try:
                current_time = time.time()

                # Update heartbeat
                if (
                    current_time - state["last_heartbeat_time"]
                    >= config["heartbeat_interval"]
                ):
                    await self.update_heartbeat()
                    state["last_heartbeat_time"] = current_time

                # Check for running jobs
                has_running_jobs = await self._check_for_running_jobs()

                if has_running_jobs:
                    if not self._waiting_for_jobs:
                        await self.log(
                            LogLevel.INFO,
                            f"Other jobs are running, waiting {config['retry_interval_seconds']} seconds before retrying",
                        )
                        self._waiting_for_jobs = True
                    await asyncio.sleep(config["retry_interval_seconds"])
                    continue

                # Reset waiting flag
                self._waiting_for_jobs = False

                # Check if generation is needed
                needs_generation = await self._check_generation_status()

                if needs_generation:
                    # Run generation job
                    await self._run_generation_job()
                else:
                    await self.log(LogLevel.DEBUG, "No resource generation needed")

                # Sleep for configured interval
                await self.log(
                    LogLevel.DEBUG,
                    f"Sleeping for {config['job_interval_seconds']} seconds",
                )
                await asyncio.sleep(config["job_interval_seconds"])

            except asyncio.CancelledError:
                await self.log(
                    LogLevel.INFO,
                    "Auto Stash Generation Daemon received shutdown signal",
                )
                break
            except Exception as e:
                await self.log(
                    LogLevel.ERROR,
                    f"Auto Stash Generation Daemon error: {str(e)}\n"
                    f"Stack trace:\n{traceback.format_exc()}",
                )
                if self.is_running:
                    await asyncio.sleep(30)  # Back off on error

    def _load_config(self) -> dict:
        """Load configuration with defaults."""
        return {
            "heartbeat_interval": self.config.get("heartbeat_interval", 30),
            "job_interval_seconds": self.config.get("job_interval_seconds", 3600),
            "retry_interval_seconds": self.config.get("retry_interval_seconds", 3600),
        }

    async def _check_for_running_jobs(self) -> bool:
        """Check if there are any running jobs."""
        try:
            async with AsyncSessionLocal() as db:
                # Query for any running or pending jobs
                query = select(Job).where(
                    Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
                )
                result = await db.execute(query)
                jobs = result.scalars().all()

                if jobs:
                    job_types = [job.type for job in jobs]
                    await self.log(
                        LogLevel.DEBUG,
                        f"Found {len(jobs)} running/pending jobs: {job_types}",
                    )
                    return True

                return False

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Error checking for running jobs: {str(e)}",
            )
            # Assume jobs are running on error to be safe
            return True

    async def _check_generation_status(self) -> bool:
        """Run a check generation status job and return whether generation is needed."""
        try:
            from app.core.dependencies import get_job_service

            job_service = get_job_service()

            # Create check generation job
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.CHECK_STASH_GENERATE,
                    db=db,
                    metadata={
                        "created_by": "AUTO_STASH_GENERATION_DAEMON",
                    },
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created check generation status job {job_id}",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason="Checking if resource generation is needed",
            )

            # Wait for job to complete
            job_result = await self._wait_for_job_completion(job_id)

            if not job_result:
                await self.log(
                    LogLevel.WARNING, "Check generation job failed or timed out"
                )
                return False

            # Check the result
            if job_result.status != JobStatus.COMPLETED.value:
                await self.log(
                    LogLevel.WARNING,
                    f"Check generation job completed with status {job_result.status}",
                )
                return False

            # Parse the result to see if generation is needed
            if job_result.result and isinstance(job_result.result, dict):
                needs_generation = job_result.result.get(
                    "resources_requiring_generation", False
                )

                if needs_generation:
                    resource_counts = job_result.result.get("resources_by_type", {})
                    await self.log(
                        LogLevel.INFO, f"Resources need generation: {resource_counts}"
                    )
                    return True
                else:
                    await self.log(LogLevel.DEBUG, "No resources need generation")
                    return False

            return False

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to check generation status: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )
            return False

    async def _run_generation_job(self):
        """Run a Stash metadata generation job."""
        try:
            from app.core.dependencies import get_job_service

            job_service = get_job_service()

            # Create generation job
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.STASH_GENERATE,
                    db=db,
                    metadata={
                        "created_by": "AUTO_STASH_GENERATION_DAEMON",
                    },
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created Stash metadata generation job {job_id}",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason="Running metadata generation",
            )

            # Wait for job to complete
            job_result = await self._wait_for_job_completion(job_id)

            if job_result and job_result.status == JobStatus.COMPLETED.value:
                await self.log(
                    LogLevel.INFO, "Stash metadata generation completed successfully"
                )
            else:
                status = job_result.status if job_result else "Unknown"
                await self.log(
                    LogLevel.WARNING,
                    f"Stash metadata generation completed with status: {status}",
                )

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to run generation job: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _wait_for_job_completion(
        self, job_id: str, timeout: int = 3600
    ) -> Optional[Job]:
        """
        Wait for a job to complete and return the final job state.

        Args:
            job_id: The job ID to wait for
            timeout: Maximum seconds to wait (default: 3600)

        Returns:
            The final Job object or None if timeout/error
        """
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds

        await self.log(LogLevel.DEBUG, f"Waiting for job {job_id} to complete")

        while self.is_running:
            try:
                # Check if timeout exceeded
                if time.time() - start_time > timeout:
                    await self.log(
                        LogLevel.WARNING,
                        f"Timeout waiting for job {job_id} after {timeout} seconds",
                    )
                    return None

                # Check job status
                async with AsyncSessionLocal() as db:
                    job = await db.get(Job, job_id)

                    if not job:
                        await self.log(LogLevel.WARNING, f"Job {job_id} not found")
                        return None

                    # Check if job is complete
                    if job.status in [
                        JobStatus.COMPLETED.value,
                        JobStatus.FAILED.value,
                        JobStatus.CANCELLED.value,
                    ]:
                        await self.log(
                            LogLevel.INFO,
                            f"Job {job_id} completed with status: {job.status}",
                        )

                        # Track job completion
                        await self.track_job_action(
                            job_id=job_id,
                            action=DaemonJobAction.FINISHED,
                            reason=f"Job completed with status {job.status}",
                        )

                        return job

                    # Log progress if available
                    if job.progress:
                        await self.log(
                            LogLevel.DEBUG, f"Job {job_id} progress: {job.progress}%"
                        )

                # Wait before checking again
                await asyncio.sleep(check_interval)

            except Exception as e:
                await self.log(
                    LogLevel.ERROR, f"Error checking job {job_id} status: {str(e)}"
                )
                return None

        # Daemon is stopping
        await self.log(LogLevel.INFO, f"Daemon stopping while waiting for job {job_id}")
        return None
