"""Auto Video Analysis Daemon - automatically analyzes scenes without video analysis."""

import asyncio
import time
import traceback
from typing import Set

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.daemons.base import BaseDaemon
from app.models import AnalysisPlan, Scene
from app.models.analysis_plan import PlanStatus
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType


class AutoVideoAnalysisDaemon(BaseDaemon):
    """
    Daemon that automatically analyzes scenes that haven't had video analysis performed.

    This daemon:
    1. Checks for scenes without video_analyzed=True
    2. Creates video tag analysis jobs in batches
    3. Monitors job completion
    4. Automatically approves and applies generated plans

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between analysis checks (default: 600)
        batch_size (int): Number of scenes to analyze per batch (default: 50)
        auto_approve_plans (bool): Whether to automatically approve and apply plans (default: True)
    """

    daemon_type = DaemonType.AUTO_VIDEO_ANALYSIS_DAEMON

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        self._pending_plan_jobs: dict[str, int] = {}  # job_id -> plan_id mapping
        self._batch_counter = 0  # Track batch numbers across processing cycles
        self._initial_total_pending = (
            0  # Track initial total for consistent batch count
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

                # If no jobs are being monitored, check for new scenes to analyze
                if not self._monitored_jobs:
                    await self._check_and_analyze_scenes(config)

                # Sleep for configured interval
                await asyncio.sleep(config["job_interval_seconds"])

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
            "auto_approve_plans": self.config.get("auto_approve_plans", True),
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
                # Reset counters when all scenes are processed
                self._batch_counter = 0
                self._initial_total_pending = 0
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

            # Create video tag analysis job
            await self._create_analysis_job(scene_ids)

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
                f"Created video tag analysis job {job_id} for {len(scene_ids)} scenes",
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

                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.FINISHED,
                        reason=f"Job completed with status {job.status}",
                    )

                    # Only handle completed analysis jobs for plan creation
                    # APPLY_PLAN jobs should not trigger another apply
                    if (
                        job.status == JobStatus.COMPLETED.value
                        and job.type == JobType.ANALYSIS.value
                        and config["auto_approve_plans"]
                    ):
                        await self._handle_completed_analysis_job(job_id, job)

                    completed_jobs.add(job_id)

        # Remove completed jobs from monitoring
        self._monitored_jobs -= completed_jobs

    async def _handle_completed_analysis_job(self, job_id: str, job: Job):
        """Handle a completed analysis job by checking for and applying any generated plan."""
        try:
            # Check if job generated a plan
            if not job.result or not isinstance(job.result, dict):
                await self.log(LogLevel.DEBUG, f"Job {job_id} has no result data")
                return

            plan_id = job.result.get("plan_id")
            if not plan_id:
                await self.log(LogLevel.DEBUG, f"Job {job_id} did not generate a plan")
                return

            # Convert plan_id to integer if it's a string
            if isinstance(plan_id, str):
                plan_id = int(plan_id)

            await self.log(
                LogLevel.INFO,
                f"Job {job_id} generated plan {plan_id}, creating apply job",
            )

            # Check plan status
            async with AsyncSessionLocal() as db:
                plan = await db.get(AnalysisPlan, plan_id)
                if not plan:
                    await self.log(LogLevel.WARNING, f"Plan {plan_id} not found")
                    return

                # Check if plan has already been applied or is being applied
                if plan.status in [PlanStatus.APPLIED, PlanStatus.REVIEWING]:
                    await self.log(
                        LogLevel.INFO,
                        f"Plan {plan_id} already applied or being applied (status: {plan.status})",
                    )
                    return

                # Check if there are any approved changes to apply
                from sqlalchemy import func, or_, select

                from app.models import PlanChange
                from app.models.plan_change import ChangeStatus

                # For auto_approve=True, we check for APPROVED and PENDING changes (not yet APPLIED)
                count_query = select(func.count(PlanChange.id)).where(
                    PlanChange.plan_id == plan_id,
                    or_(
                        PlanChange.status == ChangeStatus.APPROVED,
                        PlanChange.status == ChangeStatus.PENDING,
                    ),
                )
                count_result = await db.execute(count_query)
                unapplied_changes = count_result.scalar_one()

                if unapplied_changes == 0:
                    await self.log(
                        LogLevel.INFO,
                        f"Plan {plan_id} has no unapplied changes to apply",
                    )
                    # Mark plan as applied if all changes have been processed
                    plan.status = PlanStatus.APPLIED
                    await db.commit()
                    return

            # Create apply plan job
            await self._create_apply_plan_job(plan_id)

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to handle completed analysis job {job_id}: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )

    async def _create_apply_plan_job(self, plan_id: int):
        """Create a job to apply an analysis plan."""
        try:
            from app.core.dependencies import get_job_service

            job_service = get_job_service()

            # Create job metadata for applying plan
            job_metadata = {
                "plan_id": str(plan_id),
                "auto_approve": True,
                "created_by": "AUTO_VIDEO_ANALYSIS_DAEMON",
            }

            # Create job using job service
            async with AsyncSessionLocal() as db:
                job = await job_service.create_job(
                    job_type=JobType.APPLY_PLAN,
                    db=db,
                    metadata=job_metadata,
                )
                await db.commit()
                job_id = str(job.id)

            await self.log(
                LogLevel.INFO,
                f"Created apply plan job {job_id} for plan {plan_id}",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Apply plan {plan_id}",
            )

            # Add to monitored jobs with plan association
            self._monitored_jobs.add(job_id)
            self._pending_plan_jobs[job_id] = plan_id

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to create apply plan job for plan {plan_id}: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )
