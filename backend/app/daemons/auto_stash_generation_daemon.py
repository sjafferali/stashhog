"""Auto Stash Generation Daemon - automatically generates resources in Stash."""

import asyncio
import time
import traceback
from typing import Optional

from sqlalchemy import false, select

from app.core.database import AsyncSessionLocal
from app.daemons.base import BaseDaemon
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType
from app.models.scene import Scene


class AutoStashGenerationDaemon(BaseDaemon):
    """
    Daemon that automatically generates resources in Stash when needed.

    This daemon:
    1. Checks for running/pending jobs and skips if any are active
    2. Checks if any scenes are missing the generated attribute
    3. Starts a Stash Generate Metadata job if needed
    4. Monitors the job and cancels if scan jobs are detected
    5. Sleeps for a configured interval before repeating

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between generation checks (default: 3600)
    """

    daemon_type = DaemonType.AUTO_STASH_GENERATION_DAEMON

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._current_generation_job_id: Optional[str] = None
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

                # Step 1: Check for running/pending jobs
                has_running_jobs = await self._check_for_running_jobs()
                if has_running_jobs:
                    await self.log(
                        LogLevel.INFO,
                        f"Jobs are running, skipping generation check and sleeping for {config['job_interval_seconds']} seconds",
                    )
                    await self._sleep_with_heartbeat(
                        config["job_interval_seconds"], config["heartbeat_interval"]
                    )
                    continue

                # Step 2: Check if any scenes are missing the generated attribute
                has_ungenerated_scenes = await self._check_for_ungenerated_scenes()
                if not has_ungenerated_scenes:
                    await self.log(
                        LogLevel.DEBUG,
                        f"All scenes have generated attribute set, sleeping for {config['job_interval_seconds']} seconds",
                    )
                    await self._sleep_with_heartbeat(
                        config["job_interval_seconds"], config["heartbeat_interval"]
                    )
                    continue

                # Step 3: Start a Stash Generate Metadata job and monitor it
                await self._run_and_monitor_generation_job()

                # Step 4: Sleep for configured interval
                await self.log(
                    LogLevel.DEBUG,
                    f"Generation cycle complete, sleeping for {config['job_interval_seconds']} seconds",
                )
                await self._sleep_with_heartbeat(
                    config["job_interval_seconds"], config["heartbeat_interval"]
                )

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

    async def _check_for_ungenerated_scenes(self) -> bool:
        """Check if there are any scenes missing the generated attribute."""
        try:
            async with AsyncSessionLocal() as db:
                # Query for scenes where generated is False
                query = select(Scene).where(Scene.generated == false()).limit(1)
                result = await db.execute(query)
                scene = result.scalar_one_or_none()

                if scene:
                    # Count total ungenerated scenes for logging
                    count_query = select(Scene).where(Scene.generated == false())
                    count_result = await db.execute(count_query)
                    ungenerated_count = len(count_result.scalars().all())

                    await self.log(
                        LogLevel.INFO,
                        f"Found {ungenerated_count} scenes with generated=false",
                    )
                    return True
                else:
                    await self.log(
                        LogLevel.DEBUG,
                        "All scenes have generated attribute set to true",
                    )
                    return False

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Error checking for ungenerated scenes: {str(e)}",
            )
            # Assume scenes need generation on error to be safe
            return True

    async def _run_and_monitor_generation_job(self):
        """Run a Stash metadata generation job and monitor it, cancelling if scan jobs are detected."""
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
                self._current_generation_job_id = job_id

            await self.log(
                LogLevel.INFO,
                f"Created Stash metadata generation job {job_id}",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason="Running metadata generation for scenes with generated=false",
            )

            # Monitor the job with scan job detection
            job_cancelled = False
            config = self._load_config()
            last_heartbeat_time = time.time()

            while self.is_running:
                current_time = time.time()

                # Update heartbeat periodically during monitoring
                if current_time - last_heartbeat_time >= config["heartbeat_interval"]:
                    await self.update_heartbeat()
                    last_heartbeat_time = current_time

                # Check job status
                async with AsyncSessionLocal() as db:
                    job = await db.get(Job, job_id)

                    if not job:
                        await self.log(LogLevel.WARNING, f"Job {job_id} not found")
                        break

                    # Check if job is complete
                    if job.status in [
                        JobStatus.COMPLETED.value,
                        JobStatus.FAILED.value,
                        JobStatus.CANCELLED.value,
                    ]:
                        await self.log(
                            LogLevel.INFO,
                            f"Generation job {job_id} completed with status: {job.status}",
                        )

                        # Track job completion
                        await self.track_job_action(
                            job_id=job_id,
                            action=DaemonJobAction.FINISHED,
                            reason=f"Job completed with status {job.status}",
                        )

                        # Report to daemon
                        if job.status == JobStatus.COMPLETED.value:
                            await self.log(
                                LogLevel.INFO,
                                "Stash metadata generation completed successfully",
                            )
                        else:
                            await self.log(
                                LogLevel.WARNING,
                                f"Stash metadata generation completed with status: {job.status}",
                            )
                        break

                    # Log progress if available
                    if job.progress:
                        await self.log(
                            LogLevel.DEBUG, f"Generation job progress: {job.progress}%"
                        )

                    # Check for scan jobs
                    scan_query = select(Job).where(
                        Job.status.in_(
                            [JobStatus.PENDING.value, JobStatus.RUNNING.value]
                        ),
                        Job.type == JobType.STASH_SCAN.value,
                    )
                    scan_result = await db.execute(scan_query)
                    scan_jobs = scan_result.scalars().all()

                    if scan_jobs and not job_cancelled:
                        await self.log(
                            LogLevel.INFO,
                            f"Detected {len(scan_jobs)} scan jobs, cancelling generation job {job_id}",
                        )

                        # Cancel the generation job
                        await job_service.cancel_job(job_id, db)
                        await db.commit()

                        # Track the cancellation
                        await self.track_job_action(
                            job_id=job_id,
                            action=DaemonJobAction.CANCELLED,
                            reason="Cancelled due to detected scan jobs",
                        )

                        job_cancelled = True
                        # Continue monitoring to wait for cancellation to complete

                # Sleep for 30 seconds before checking again
                await asyncio.sleep(30)

            # Clear current job ID
            self._current_generation_job_id = None

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to run generation job: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )
            self._current_generation_job_id = None

    async def _sleep_with_heartbeat(self, sleep_duration: int, heartbeat_interval: int):
        """Sleep for a duration while periodically updating heartbeat."""
        elapsed = 0
        while elapsed < sleep_duration and self.is_running:
            # Sleep for the minimum of remaining time or heartbeat interval
            sleep_time = min(heartbeat_interval, sleep_duration - elapsed)
            await asyncio.sleep(sleep_time)
            elapsed += sleep_time

            # Update heartbeat if we've slept for the heartbeat interval
            if elapsed % heartbeat_interval == 0 or elapsed >= sleep_duration:
                await self.update_heartbeat()
