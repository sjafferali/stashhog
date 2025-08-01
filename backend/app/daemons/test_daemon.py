import asyncio
import time
import uuid
from typing import Set

from app.core.database import AsyncSessionLocal
from app.daemons.base import BaseDaemon
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType


class TestDaemon(BaseDaemon):
    """
    Test daemon that demonstrates all daemon capabilities.

    Features demonstrated:
    - Heartbeat mechanism
    - Real-time logging at different levels
    - Job launching and monitoring
    - Configuration handling
    - Graceful shutdown
    - Error recovery

    Configuration:
        log_interval (int): Seconds between log messages (default: 5)
        job_interval (int): Seconds between job launches (default: 30)
        heartbeat_interval (int): Seconds between heartbeat updates (default: 10)
        simulate_errors (bool): Whether to simulate errors (default: False)
    """

    daemon_type = DaemonType.TEST_DAEMON

    async def on_start(self):
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        await self.log(LogLevel.INFO, "TestDaemon initialized successfully")

    async def on_stop(self):
        """Clean up daemon-specific resources."""
        await self.log(
            LogLevel.INFO,
            f"TestDaemon shutting down. Monitored {len(self._monitored_jobs)} jobs. "
            f"Uptime: {self.get_uptime_seconds():.1f} seconds",
        )
        await super().on_stop()

    async def run(self):
        """Main daemon execution loop."""
        # Configuration with defaults
        config = self._load_config()
        await self.log(LogLevel.INFO, f"TestDaemon started with config: {self.config}")

        state = {"last_job_time": 0, "last_heartbeat_time": 0, "counter": 0}

        while self.is_running:
            try:
                await self._run_iteration(config, state)
            except asyncio.CancelledError:
                # Graceful shutdown
                await self.log(LogLevel.INFO, "TestDaemon received shutdown signal")
                break
            except Exception as e:
                # Error recovery
                await self.log(LogLevel.ERROR, f"TestDaemon error: {str(e)}")
                if self.is_running:
                    await asyncio.sleep(5)  # Back off before retrying

    def _load_config(self) -> dict:
        """Load configuration with defaults."""
        return {
            "log_interval": self.config.get("log_interval", 5),
            "job_interval": self.config.get("job_interval", 30),
            "heartbeat_interval": self.config.get("heartbeat_interval", 10),
            "simulate_errors": self.config.get("simulate_errors", False),
        }

    async def _run_iteration(self, config: dict, state: dict):
        """Run a single iteration of the daemon loop."""
        current_time = time.time()
        state["counter"] += 1

        # Heartbeat update
        if current_time - state["last_heartbeat_time"] >= config["heartbeat_interval"]:
            await self.update_heartbeat()
            state["last_heartbeat_time"] = current_time

        # Perform logging
        await self._perform_logging(state["counter"])

        # Simulate error condition
        if config["simulate_errors"] and state["counter"] % 20 == 0:
            raise Exception("Simulated error for testing")

        # Launch a test job periodically
        if current_time - state["last_job_time"] >= config["job_interval"]:
            await self._launch_test_job(state["counter"])
            state["last_job_time"] = current_time

        # Check for any jobs we're monitoring
        await self._check_monitored_jobs()

        # Sleep for the configured interval
        await asyncio.sleep(config["log_interval"])

    async def _perform_logging(self, counter: int):
        """Perform periodic logging at different levels."""
        # Regular logging to demonstrate real-time logs
        await self.log(LogLevel.DEBUG, f"Test daemon iteration {counter}")

        # Demonstrate different log levels
        if counter % 5 == 0:
            await self.log(
                LogLevel.INFO,
                f"Status check #{counter}: Memory usage: {self._get_memory_usage()}MB, "
                f"Monitored jobs: {len(self._monitored_jobs)}",
            )

        if counter % 10 == 0:
            await self.log(
                LogLevel.WARNING,
                f"This is a test warning at iteration {counter}",
            )

    async def _launch_test_job(self, iteration: int):
        """Launch a test job to demonstrate job orchestration."""
        try:
            job_name = f"test_job_{iteration}"
            job_id = str(uuid.uuid4())

            # Create a test job using dedicated session
            async with AsyncSessionLocal() as db:
                job = Job(
                    id=job_id,
                    type=JobType.TEST.value,
                    status=JobStatus.PENDING.value,
                    job_metadata={
                        "daemon_id": str(self.daemon_id),
                        "iteration": iteration,
                        "created_by": "TestDaemon",
                        "name": job_name,  # Store name in metadata
                    },
                )
                db.add(job)
                await db.commit()

            await self.log(
                LogLevel.INFO, f"Launched test job: {job_name} (ID: {job_id})"
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Test job for iteration {iteration}",
            )

            # Add to monitored jobs
            self._monitored_jobs.add(job_id)

            # Submit to job service (this will actually run the job)
            # await job_service.submit_job(job_id)  # TODO: Implement job submission

        except Exception as e:
            await self.log(LogLevel.ERROR, f"Failed to launch test job: {str(e)}")

    async def _check_monitored_jobs(self):
        """Check status of jobs we're monitoring."""
        if not self._monitored_jobs:
            return

        completed_jobs = set()

        async with AsyncSessionLocal() as db:
            for job_id in self._monitored_jobs:
                job = await db.get(Job, job_id)
                if job and job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    job_name = (
                        job.job_metadata.get("name", job.id)
                        if job.job_metadata
                        else job.id
                    )
                    await self.log(
                        LogLevel.INFO,
                        f"Monitored job {job_name} completed with status: {job.status}",
                    )

                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.MONITORED,
                        reason=f"Job completed with status {job.status}",
                    )

                    completed_jobs.add(job_id)

        # Remove completed jobs from monitoring
        self._monitored_jobs -= completed_jobs

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return float(round(memory_mb, 2))
        except ImportError:
            # psutil not available, return 0
            return 0.0
