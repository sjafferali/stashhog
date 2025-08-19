"""Auto Stash Sync Daemon - automatically syncs scenes pending from Stash."""

import asyncio
import time
import traceback
from typing import Optional, Set

from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_job_service
from app.core.settings_loader import load_settings_with_db_overrides
from app.daemons.base import BaseDaemon
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType
from app.services.stash_service import StashService
from app.services.sync_status_service import SyncStatusService


class AutoStashSyncDaemon(BaseDaemon):
    """
    Daemon that automatically syncs scenes that have been updated in Stash.

    This daemon:
    1. Checks if there are any scenes pending sync from Stash
    2. Creates an incremental sync job if needed and waits for it to complete
    3. Logs the sync execution with the number of pending scenes
    4. Sleeps for the configured interval

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between sync checks (default: 300)
    """

    daemon_type = DaemonType.AUTO_STASH_SYNC_DAEMON

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        self._stash_service: Optional[StashService] = None
        self._sync_status_service: Optional[SyncStatusService] = None
        self._last_job_completion_time: float = 0  # Track when last job completed
        await self.log(LogLevel.INFO, "Auto Stash Sync Daemon initialized")

    async def on_stop(self) -> None:
        """Clean up daemon-specific resources."""
        await self.log(
            LogLevel.INFO,
            f"Auto Stash Sync Daemon shutting down. "
            f"Monitored {len(self._monitored_jobs)} jobs. "
            f"Uptime: {self.get_uptime_seconds():.1f} seconds",
        )
        await super().on_stop()

    async def run(self):
        """Main daemon execution loop."""
        config = self._load_config()
        await self.log(
            LogLevel.INFO, f"Auto Stash Sync Daemon started with config: {config}"
        )

        # Initialize services
        await self._initialize_services()

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

                # Check monitored jobs
                await self._check_monitored_jobs()

                # If no jobs are being monitored, check for pending scenes
                if not self._monitored_jobs:
                    # Check if enough time has passed since last job completion
                    time_since_last_job = current_time - self._last_job_completion_time

                    if time_since_last_job >= config["job_interval_seconds"]:
                        # Enough time has passed, check for pending scenes
                        await self._check_and_sync_scenes(config)
                        # Only sleep for the full interval if no job was created
                        if not self._monitored_jobs:
                            await asyncio.sleep(config["job_interval_seconds"])
                        else:
                            # Job was created, check more frequently
                            await asyncio.sleep(5)
                    else:
                        # Wait the remaining time before checking again
                        remaining_time = (
                            config["job_interval_seconds"] - time_since_last_job
                        )
                        await self.log(
                            LogLevel.DEBUG,
                            f"Waiting {remaining_time:.1f}s before next sync check "
                            f"(last job completed {time_since_last_job:.1f}s ago)",
                        )
                        await asyncio.sleep(
                            min(remaining_time, 30)
                        )  # Check at least every 30s for heartbeat
                else:
                    # Jobs are being monitored, check status frequently
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                await self.log(
                    LogLevel.INFO, "Auto Stash Sync Daemon received shutdown signal"
                )
                break
            except Exception as e:
                await self.log(
                    LogLevel.ERROR,
                    f"Auto Stash Sync Daemon error: {str(e)}\n"
                    f"Stack trace:\n{traceback.format_exc()}",
                )
                if self.is_running:
                    await asyncio.sleep(30)  # Back off on error

    def _load_config(self) -> dict:
        """Load configuration with defaults."""
        return {
            "heartbeat_interval": self.config.get("heartbeat_interval", 30),
            "job_interval_seconds": self.config.get("job_interval_seconds", 300),
        }

    async def _initialize_services(self):
        """Initialize Stash and Sync Status services."""
        try:
            settings = await load_settings_with_db_overrides()

            self._stash_service = StashService(
                stash_url=settings.stash.url, api_key=settings.stash.api_key
            )
            self._sync_status_service = SyncStatusService(self._stash_service)
        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to initialize services: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )
            raise

    async def _check_and_sync_scenes(self, config: dict):
        """Check for scenes pending sync and create job if needed."""
        try:
            if not self._sync_status_service:
                await self.log(
                    LogLevel.ERROR,
                    "Sync status service not initialized",
                )
                return

            async with AsyncSessionLocal() as db:
                # Get pending scenes count from centralized service
                pending_scenes = (
                    await self._sync_status_service.get_pending_scenes_count(db)
                )

                if pending_scenes == 0:
                    await self.log(LogLevel.DEBUG, "No scenes pending sync from Stash")
                    return

                await self.log(
                    LogLevel.INFO,
                    f"Found {pending_scenes} scenes pending sync from Stash",
                )

                # Create incremental sync job
                await self._create_sync_job(pending_scenes)

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to check for pending scenes: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _create_sync_job(self, pending_scenes: int):
        """Create an incremental sync job."""
        try:
            job_service = get_job_service()

            # Create job metadata for incremental sync
            job_metadata = {
                "force": False,  # Incremental sync
                "created_by": "AUTO_STASH_SYNC_DAEMON",
                "pending_scenes": pending_scenes,
            }

            # Create job using job service
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.SYNC,
                    db=db,
                    metadata=job_metadata,
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created incremental sync job {job_id} for {pending_scenes} pending scenes",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Incremental sync for {pending_scenes} pending scenes",
            )

            # Add to monitored jobs
            self._monitored_jobs.add(job_id)

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to create sync job: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _check_monitored_jobs(self):
        """Check status of monitored jobs and handle completion."""
        if not self._monitored_jobs:
            return

        completed_jobs = set()

        async with AsyncSessionLocal() as db:
            # Create a copy to avoid "Set changed size during iteration" error
            for job_id in list(self._monitored_jobs):
                job = await db.get(Job, job_id)
                if not job:
                    await self.log(
                        LogLevel.WARNING,
                        f"Job {job_id} not found in database, removing from monitoring",
                    )
                    completed_jobs.add(job_id)
                    continue

                # Log current job status for debugging
                await self.log(
                    LogLevel.DEBUG,
                    f"Monitoring job {job_id}: status={job.status}",
                )

                # Check if job has finished
                if job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    # Get the number of scenes that were pending
                    pending_scenes = (
                        job.job_metadata.get("pending_scenes", 0)
                        if job.job_metadata
                        else 0
                    )

                    if job.status == JobStatus.COMPLETED.value:
                        await self.log(
                            LogLevel.INFO,
                            f"Executed incremental sync due to {pending_scenes} scenes that needed to be resynced. "
                            f"Job {job_id} completed successfully.",
                        )
                    elif job.status == JobStatus.CANCELLED.value:
                        await self.log(
                            LogLevel.WARNING,
                            f"Sync job {job_id} was cancelled. Will wait {self.config.get('job_interval_seconds', 300)}s before checking again.",
                        )
                    else:
                        await self.log(
                            LogLevel.WARNING,
                            f"Sync job {job_id} completed with status: {job.status}",
                        )

                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.FINISHED,
                        reason=f"Job completed with status {job.status}",
                    )

                    # Record completion time
                    self._last_job_completion_time = time.time()

                    completed_jobs.add(job_id)

        # Remove completed jobs from monitoring
        if completed_jobs:
            self._monitored_jobs -= completed_jobs
            await self.log(
                LogLevel.DEBUG,
                f"Removed {len(completed_jobs)} completed jobs from monitoring. "
                f"Still monitoring {len(self._monitored_jobs)} jobs.",
            )
