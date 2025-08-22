"""Download Processor Daemon - automatically processes completed downloads."""

import asyncio
import time
import traceback
from typing import Any, Dict, Optional, Set

from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_job_service
from app.daemons.base import BaseDaemon
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType
from app.services.download_check_service import download_check_service


class DownloadProcessorDaemon(BaseDaemon):
    """
    Daemon that automatically processes completed downloads from qBittorrent.

    This daemon:
    1. Checks if there are any downloads that need to be processed (completed torrents without 'synced' tag)
    2. If downloads need processing, launches a PROCESS_DOWNLOADS job and waits for completion
    3. Logs each download name that is processed along with the count of files processed
    4. If items were processed, starts a STASH_SCAN job with default arguments and waits for completion
    5. Sleeps for the configured interval

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between processing checks (default: 300)
    """

    daemon_type = DaemonType.DOWNLOAD_PROCESSOR_DAEMON

    @classmethod
    def get_default_config(cls) -> dict:
        """Get the default configuration for this daemon."""
        return {
            "heartbeat_interval": 30,
            "job_interval_seconds": 300,
            "_descriptions": {
                "heartbeat_interval": "Seconds between heartbeat updates to indicate daemon health",
                "job_interval_seconds": "Seconds to wait between checking for completed downloads to process",
            },
        }

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        self._current_job_type: Optional[JobType] = None
        self._just_completed_cycle = False
        await self.log(LogLevel.INFO, "Download Processor Daemon initialized")

    async def on_stop(self) -> None:
        """Clean up daemon-specific resources."""
        await self.log(
            LogLevel.INFO,
            f"Download Processor Daemon shutting down. "
            f"Monitored {len(self._monitored_jobs)} jobs. "
            f"Uptime: {self.get_uptime_seconds():.1f} seconds",
        )
        await super().on_stop()

    async def run(self):
        """Main daemon execution loop."""
        config = self._load_config()
        await self.log(
            LogLevel.INFO, f"Download Processor Daemon started with config: {config}"
        )

        state = {"last_heartbeat_time": 0}

        while self.is_running:
            try:
                current_time = time.time()

                # Update heartbeat if needed
                if (
                    current_time - state["last_heartbeat_time"]
                    >= config["heartbeat_interval"]
                ):
                    await self.update_heartbeat()
                    state["last_heartbeat_time"] = current_time

                # Process one iteration of the daemon loop
                sleep_duration = await self._process_iteration(config)
                await asyncio.sleep(sleep_duration)

            except asyncio.CancelledError:
                await self.log(
                    LogLevel.INFO, "Download Processor Daemon received shutdown signal"
                )
                break
            except Exception as e:
                await self.log(
                    LogLevel.ERROR,
                    f"Download Processor Daemon error: {str(e)}\n"
                    f"Stack trace:\n{traceback.format_exc()}",
                )
                if self.is_running:
                    await asyncio.sleep(30)  # Back off on error

    async def _process_iteration(self, config: dict) -> int:
        """Process one iteration of the daemon loop.

        Returns:
            Sleep duration in seconds before next iteration
        """
        # Check monitored jobs
        completed_job_result = await self._check_monitored_jobs()

        # If jobs are being monitored, check frequently
        if self._monitored_jobs:
            return 5

        # Handle completed process downloads job
        if await self._handle_completed_download_job(completed_job_result):
            return 5

        # If we just completed a cycle (all jobs finished), sleep for the full interval
        if self._just_completed_cycle:
            self._just_completed_cycle = False
            return int(config["job_interval_seconds"])

        # Check for new downloads to process
        await self._check_and_process_downloads(config)

        # Return appropriate sleep duration
        return 5 if self._monitored_jobs else int(config["job_interval_seconds"])

    async def _handle_completed_download_job(
        self, completed_job_result: Optional[dict]
    ) -> bool:
        """Handle a completed download processing job.

        Args:
            completed_job_result: Result from completed job or None

        Returns:
            True if a follow-up job was created, False otherwise
        """
        if not completed_job_result:
            return False

        if completed_job_result.get("type") != JobType.PROCESS_DOWNLOADS.value:
            return False

        synced_items = completed_job_result.get("synced_items", 0)
        if synced_items > 0:
            await self.log(
                LogLevel.INFO,
                f"Process downloads job completed with {synced_items} items processed. "
                f"Starting Stash metadata scan.",
            )
            await self._create_stash_scan_job()
            return True

        return False

    def _load_config(self) -> dict:
        """Load configuration with defaults."""
        return {
            "heartbeat_interval": self.config.get("heartbeat_interval", 30),
            "job_interval_seconds": self.config.get("job_interval_seconds", 300),
        }

    async def _check_and_process_downloads(self, config: dict):
        """Check for downloads needing processing and create job if needed."""
        try:
            # Get pending downloads count
            pending_count = await download_check_service.get_pending_downloads_count()

            if pending_count == 0:
                await self.log(LogLevel.DEBUG, "No downloads pending processing")
                return

            await self.log(
                LogLevel.INFO,
                f"Found {pending_count} downloads pending processing",
            )

            # Create process downloads job
            await self._create_process_downloads_job(pending_count)

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to check for pending downloads: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _create_process_downloads_job(self, pending_count: int):
        """Create a process downloads job."""
        try:
            job_service = get_job_service()

            # Create job metadata
            job_metadata = {
                "exclude_small_vids": False,  # Default setting
                "created_by": "DOWNLOAD_PROCESSOR_DAEMON",
                "pending_downloads": pending_count,
            }

            # Create job using job service
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.PROCESS_DOWNLOADS,
                    db=db,
                    metadata=job_metadata,
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created process downloads job {job_id} for {pending_count} pending downloads",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Process {pending_count} pending downloads",
            )

            # Add to monitored jobs
            self._monitored_jobs.add(job_id)
            self._current_job_type = JobType.PROCESS_DOWNLOADS

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to create process downloads job: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _create_stash_scan_job(self):
        """Create a Stash metadata scan job."""
        try:
            job_service = get_job_service()

            # Create job metadata with default arguments
            job_metadata = {
                "paths": ["/data"],
                "rescan": False,
                "scanGenerateCovers": True,
                "scanGeneratePreviews": True,
                "scanGenerateImagePreviews": False,
                "scanGenerateSprites": True,
                "scanGeneratePhashes": True,
                "scanGenerateThumbnails": False,
                "scanGenerateClipPreviews": False,
                "created_by": "DOWNLOAD_PROCESSOR_DAEMON",
            }

            # Create job using job service
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.STASH_SCAN,
                    db=db,
                    metadata=job_metadata,
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created Stash metadata scan job {job_id}",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason="Scan new content after processing downloads",
            )

            # Add to monitored jobs
            self._monitored_jobs.add(job_id)
            self._current_job_type = JobType.STASH_SCAN

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to create Stash scan job: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _check_monitored_jobs(self) -> Optional[dict]:
        """Check status of monitored jobs and handle completion.

        Returns:
            Dict with job result information if a job completed, None otherwise
        """
        if not self._monitored_jobs:
            return None

        completed_jobs = set()
        completed_job_result = None

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
                    f"Monitoring job {job_id}: type={job.type}, status={job.status}",
                )

                # Check if job has finished
                if job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    # Handle based on job type
                    if job.type == JobType.PROCESS_DOWNLOADS.value:
                        await self._handle_process_downloads_completion(job)
                        # Store result for further processing
                        if job.status == JobStatus.COMPLETED.value and job.result:
                            completed_job_result = {
                                "type": job.type,
                                "synced_items": job.result.get("synced_items", 0),
                                "total_files_linked": job.result.get(
                                    "total_files_linked", 0
                                ),
                            }
                    elif job.type == JobType.STASH_SCAN.value:
                        await self._handle_stash_scan_completion(job)

                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.FINISHED,
                        reason=f"Job completed with status {job.status}",
                    )

                    completed_jobs.add(job_id)

        # Remove completed jobs from monitoring
        if completed_jobs:
            self._monitored_jobs -= completed_jobs
            self._current_job_type = None

            # If we just finished all jobs, mark that we completed a cycle
            if len(self._monitored_jobs) == 0:
                self._just_completed_cycle = True

            await self.log(
                LogLevel.DEBUG,
                f"Removed {len(completed_jobs)} completed jobs from monitoring. "
                f"Still monitoring {len(self._monitored_jobs)} jobs.",
            )

        return completed_job_result

    async def _handle_process_downloads_completion(self, job: Job):
        """Handle completion of a process downloads job."""
        if job.status == JobStatus.COMPLETED.value:
            # Extract results from job
            result: Dict[str, Any] = job.result if isinstance(job.result, dict) else {}
            processed_items = result.get("processed_items", 0)
            synced_items = result.get("synced_items", 0)
            total_files_linked = result.get("total_files_linked", 0)
            failed_items = result.get("failed_items", 0)

            # Log details of processed downloads
            if synced_items > 0:
                await self.log(
                    LogLevel.INFO,
                    f"Process downloads job {job.id} completed successfully. "
                    f"Processed {processed_items} downloads, "
                    f"synced {synced_items} items, "
                    f"linked {total_files_linked} files.",
                )

                # Log individual download names if available in metadata
                if (
                    job.job_metadata
                    and isinstance(job.job_metadata, dict)
                    and "download_names" in job.job_metadata
                ):
                    for download_name in job.job_metadata.get("download_names", []):
                        await self.log(
                            LogLevel.INFO,
                            f"Processed download: {download_name}",
                        )
            else:
                await self.log(
                    LogLevel.INFO,
                    f"Process downloads job {job.id} completed with no items to sync.",
                )

            if failed_items > 0:
                await self.log(
                    LogLevel.WARNING,
                    f"Process downloads job had {failed_items} failed items",
                )
        else:
            await self.log(
                LogLevel.WARNING,
                f"Process downloads job {job.id} completed with status: {job.status}",
            )

    async def _handle_stash_scan_completion(self, job: Job):
        """Handle completion of a Stash scan job."""
        if job.status == JobStatus.COMPLETED.value:
            await self.log(
                LogLevel.INFO,
                f"Stash metadata scan job {job.id} completed successfully",
            )
        else:
            await self.log(
                LogLevel.WARNING,
                f"Stash scan job {job.id} completed with status: {job.status}",
            )
