"""Auto Video Analysis Daemon - automatically analyzes scenes without video analysis."""

import asyncio
import time
import traceback
from typing import Set

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.daemons.base import BaseDaemon
from app.models import Scene
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType


class AutoVideoAnalysisDaemon(BaseDaemon):
    """
    Daemon that automatically analyzes scenes that haven't had video analysis performed.

    This daemon:
    1. Checks for scenes without video_analyzed=True
    2. Creates video tag analysis jobs in batches
    3. Monitors job completion

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between analysis checks (default: 600)
        batch_size (int): Number of scenes to analyze per batch (default: 50)
    """

    daemon_type = DaemonType.AUTO_VIDEO_ANALYSIS_DAEMON

    @classmethod
    def get_default_config(cls) -> dict:
        """Get the default configuration for this daemon."""
        return {
            "heartbeat_interval": 30,
            "job_interval_seconds": 600,
            "batch_size": 50,
            "_descriptions": {
                "heartbeat_interval": "Seconds between heartbeat updates to indicate daemon health",
                "job_interval_seconds": "Seconds to wait between checking for scenes needing video analysis",
                "batch_size": "Number of scenes to analyze in each batch",
            },
        }

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        self._batch_counter = 0  # Track batch numbers across processing cycles
        self._initial_total_pending = (
            0  # Track initial total for consistent batch count
        )
        self._last_check_time = 0.0  # Track when we last checked for new scenes
        self._waiting_status_set = (
            False  # Track if we've already set the waiting status
        )
        await self.log(LogLevel.INFO, "Auto Video Analysis Daemon initialized")

    async def on_stop(self) -> None:
        """Clean up daemon-specific resources."""
        await self.log(
            LogLevel.INFO,
            f"Auto Video Analysis Daemon shutting down. "
            f"Monitored {len(self._monitored_jobs)} jobs. "
            f"Uptime: {self.get_uptime_seconds():.1f} seconds",
        )
        await super().on_stop()

    async def run(self):
        """Main daemon execution loop."""
        config = self._load_config()
        await self.log(
            LogLevel.INFO, f"Auto Video Analysis Daemon started with config: {config}"
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

                # Check monitored jobs
                await self._check_monitored_jobs(config)

                # If no jobs are being monitored, check if enough time has passed since last check
                if not self._monitored_jobs:
                    time_since_last_check = current_time - self._last_check_time

                    # Only check for new scenes if enough time has passed
                    if time_since_last_check >= config["job_interval_seconds"]:
                        await self.log(
                            LogLevel.DEBUG,
                            f"No jobs running and {time_since_last_check:.1f}s since last check "
                            f"(>= {config['job_interval_seconds']}s interval), checking for scenes",
                        )
                        await self.update_status(
                            "Checking for scenes needing video analysis"
                        )
                        # Reset the waiting status flag since we're now checking
                        self._waiting_status_set = False
                        await self._check_and_analyze_scenes(config)
                    else:
                        # Sleep for the remaining time until next check
                        remaining_sleep = (
                            config["job_interval_seconds"] - time_since_last_check
                        )

                        # Only update status if we haven't already set it for this wait period
                        # Check if current status already indicates we're waiting
                        if (
                            not hasattr(self, "_waiting_status_set")
                            or not self._waiting_status_set
                        ):
                            await self.log(
                                LogLevel.DEBUG,
                                f"Waiting {remaining_sleep:.1f}s before next scene check",
                            )
                            await self.update_status(
                                f"Sleeping for {config['job_interval_seconds']} seconds"
                            )
                            self._waiting_status_set = True

                        # Sleep in small increments to remain responsive to shutdown
                        await asyncio.sleep(min(remaining_sleep, 1))
                else:
                    # Sleep briefly while monitoring jobs
                    await self.log(
                        LogLevel.DEBUG,
                        f"Monitoring {len(self._monitored_jobs)} active job(s), skipping scene check",
                    )
                    # Status update handled in _check_monitored_jobs
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                await self.log(
                    LogLevel.INFO, "Auto Video Analysis Daemon received shutdown signal"
                )
                break
            except Exception as e:
                await self.log(
                    LogLevel.ERROR,
                    f"Auto Video Analysis Daemon error: {str(e)}\n"
                    f"Stack trace:\n{traceback.format_exc()}",
                )
                if self.is_running:
                    await asyncio.sleep(30)  # Back off on error

    def _load_config(self) -> dict:
        """Load configuration with defaults."""
        return {
            "heartbeat_interval": self.config.get("heartbeat_interval", 30),
            "job_interval_seconds": self.config.get("job_interval_seconds", 600),
            "batch_size": self.config.get("batch_size", 50),
        }

    async def _check_and_analyze_scenes(self, config: dict):
        """Check for scenes needing video analysis and create jobs."""
        async with AsyncSessionLocal() as db:
            # Count scenes without video analysis
            count_query = select(func.count(Scene.id)).where(
                Scene.video_analyzed.is_(False)
            )
            result = await db.execute(count_query)
            total_pending = result.scalar_one()

            if total_pending == 0:
                await self.log(LogLevel.DEBUG, "No scenes pending video analysis")
                await self.update_status(
                    f"Sleeping for {config['job_interval_seconds']} seconds"
                )
                # Reset counters when all scenes are processed
                self._batch_counter = 0
                self._initial_total_pending = 0
                # CRITICAL: Update last check time to prevent rapid re-checking
                self._last_check_time = time.time()
                return

            # Initialize or update total pending tracking
            if (
                self._initial_total_pending == 0
                or total_pending > self._initial_total_pending
            ):
                # New batch sequence starting or more scenes added
                self._initial_total_pending = total_pending
                self._batch_counter = 0

            await self.log(
                LogLevel.INFO,
                f"Found {total_pending} scenes pending video analysis",
            )
            await self.update_status(f"Found {total_pending} scenes needing analysis")

            # Get batch of scenes to analyze
            batch_size = config["batch_size"]
            scenes_query = (
                select(Scene.id)
                .where(Scene.video_analyzed.is_(False))
                .limit(batch_size)
            )
            result = await db.execute(scenes_query)
            scene_ids = [str(row[0]) for row in result]

            if not scene_ids:
                return

            # Increment batch counter for this processing cycle
            self._batch_counter += 1

            # Calculate total batches based on initial total
            total_batches = (self._initial_total_pending + batch_size - 1) // batch_size

            await self.log(
                LogLevel.INFO,
                f"Processing batch {self._batch_counter} of {total_batches} "
                f"({len(scene_ids)} scenes)",
            )
            await self.update_status(
                f"Processing batch {self._batch_counter} of {total_batches} ({len(scene_ids)} scenes)"
            )

            # Create video tag analysis job
            await self._create_analysis_job(scene_ids)

            # Update last check time immediately after creating job to prevent
            # creating duplicate jobs while this one is still running
            self._last_check_time = time.time()

    async def _create_analysis_job(self, scene_ids: list[str]):
        """Create a video tag analysis job for the given scenes."""
        try:
            from app.core.dependencies import get_job_service

            job_service = get_job_service()

            # Create job metadata for video tag analysis
            job_metadata = {
                "scene_ids": scene_ids,
                "options": {
                    "detect_video_tags": True,
                    "detect_performers": False,
                    "detect_studios": False,
                    "detect_tags": False,
                    "detect_details": False,
                },
                "plan_name": f"Auto Video Analysis - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "created_by": "AUTO_VIDEO_ANALYSIS_DAEMON",
            }

            # Create job using job service
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.ANALYSIS,
                    db=db,
                    metadata=job_metadata,
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created video tag analysis job {job_id} for {len(scene_ids)} scenes. "
                f"Total monitored jobs: {len(self._monitored_jobs) + 1}",
            )

            # Update status with job information
            await self.update_status(
                f"Analyzing video tags for {len(scene_ids)} scenes",
                job_id=job_id,
                job_type=JobType.ANALYSIS.value,
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Video tag analysis for {len(scene_ids)} scenes",
            )

            # Add to monitored jobs
            self._monitored_jobs.add(job_id)

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to create video tag analysis job: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _check_monitored_jobs(self, config: dict):
        """Check status of monitored jobs and handle completion."""
        if not self._monitored_jobs:
            return

        completed_jobs = set()

        # Update status to show we're monitoring jobs
        if len(self._monitored_jobs) == 1:
            # Get the single job ID for status
            job_id = next(iter(self._monitored_jobs))
            await self.update_status(
                "Waiting for video analysis to complete",
                job_id=job_id,
                job_type=JobType.ANALYSIS.value,
            )
        else:
            await self.update_status(
                f"Monitoring {len(self._monitored_jobs)} analysis jobs"
            )

        async with AsyncSessionLocal() as db:
            # Create a copy to avoid "Set changed size during iteration" error
            for job_id in list(self._monitored_jobs):
                job = await db.get(Job, job_id)
                if not job:
                    completed_jobs.add(job_id)
                    continue

                # Check if job has finished
                if job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    await self.log(
                        LogLevel.INFO,
                        f"Job {job_id} (type: {job.type}) completed with status: {job.status}",
                    )

                    # Track job completion with the appropriate action based on status
                    if job.status == JobStatus.COMPLETED.value:
                        action = DaemonJobAction.FINISHED
                        reason = "Job completed successfully"
                    elif job.status == JobStatus.FAILED.value:
                        action = DaemonJobAction.FAILED
                        # The Job model has an 'error' field, not 'error_message'
                        reason = f"Job failed: {job.error or 'Unknown error'}"
                    else:  # CANCELLED
                        action = DaemonJobAction.CANCELLED
                        reason = "Job was cancelled"

                    await self.track_job_action(
                        job_id=job_id,
                        action=action,
                        reason=reason,
                    )

                    completed_jobs.add(job_id)

        # Remove completed jobs from monitoring
        if completed_jobs:
            self._monitored_jobs -= completed_jobs
            # Update last check time when jobs complete to start the interval timer
            self._last_check_time = time.time()
            # Reset the waiting status flag since we'll be checking for more scenes soon
            self._waiting_status_set = False

            # Update status after job completion
            if not self._monitored_jobs:
                await self.update_status("Analysis completed, checking for more scenes")
