"""Auto Plan Applier Daemon - automatically applies approved changes from analysis plans."""

import asyncio
import time
import traceback
from typing import List, Optional, Set

from sqlalchemy import func, or_, select

from app.core.database import AsyncSessionLocal
from app.daemons.base import BaseDaemon
from app.models import AnalysisPlan, PlanChange
from app.models.analysis_plan import PlanStatus
from app.models.daemon import DaemonJobAction, DaemonType, LogLevel
from app.models.job import Job, JobStatus, JobType
from app.models.plan_change import ChangeStatus


class AutoPlanApplierDaemon(BaseDaemon):
    """
    Daemon that automatically applies approved changes from analysis plans.

    This daemon:
    1. Checks for plans in DRAFT or REVIEWING status
    2. Filters plans by configured prefixes
    3. Either auto-approves all changes or applies only approved changes
    4. Creates and monitors apply plan jobs
    5. Logs the number of plans processed

    Configuration:
        heartbeat_interval (int): Seconds between heartbeat updates (default: 30)
        job_interval_seconds (int): Seconds to sleep between checks (default: 60)
        plan_prefix_filter (list): List of prefixes to filter plans by (default: [])
        auto_approve_all_changes (bool): Whether to approve and apply all changes (default: False)
    """

    daemon_type = DaemonType.AUTO_PLAN_APPLIER_DAEMON

    async def on_start(self) -> None:
        """Initialize daemon-specific resources."""
        await super().on_start()
        self._monitored_jobs: Set[str] = set()
        self._job_to_plan_mapping: dict[str, int] = {}  # job_id -> plan_id mapping
        await self.log(LogLevel.INFO, "Auto Plan Applier Daemon initialized")

    async def on_stop(self) -> None:
        """Clean up daemon-specific resources."""
        await self.log(
            LogLevel.INFO,
            f"Auto Plan Applier Daemon shutting down. "
            f"Monitored {len(self._monitored_jobs)} jobs. "
            f"Uptime: {self.get_uptime_seconds():.1f} seconds",
        )
        await super().on_stop()

    async def run(self):
        """Main daemon execution loop."""
        config = self._load_config()
        await self.log(
            LogLevel.INFO, f"Auto Plan Applier Daemon started with config: {config}"
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

                # Check monitored jobs for completion
                await self._check_monitored_jobs()

                # Process plans if no jobs are being monitored
                if not self._monitored_jobs:
                    plans_processed = await self._process_plans(config)
                    if plans_processed > 0:
                        await self.log(
                            LogLevel.INFO,
                            f"Processed {plans_processed} plan(s) for application",
                        )

                # Sleep for configured interval with heartbeat updates
                await self._sleep_with_heartbeat(
                    config["job_interval_seconds"], config["heartbeat_interval"]
                )

            except asyncio.CancelledError:
                await self.log(
                    LogLevel.INFO, "Auto Plan Applier Daemon received shutdown signal"
                )
                break
            except Exception as e:
                await self.log(
                    LogLevel.ERROR,
                    f"Auto Plan Applier Daemon error: {str(e)}\n"
                    f"Stack trace:\n{traceback.format_exc()}",
                )
                if self.is_running:
                    await asyncio.sleep(30)  # Back off on error

    def _load_config(self) -> dict:
        """Load configuration with defaults."""
        return {
            "heartbeat_interval": self.config.get("heartbeat_interval", 30),
            "job_interval_seconds": self.config.get("job_interval_seconds", 60),
            "plan_prefix_filter": self.config.get("plan_prefix_filter", []),
            "auto_approve_all_changes": self.config.get(
                "auto_approve_all_changes", False
            ),
        }

    async def _process_plans(self, config: dict) -> int:
        """Process plans according to configuration."""
        async with AsyncSessionLocal() as db:
            # Query for plans in DRAFT or REVIEWING status
            query = select(AnalysisPlan).where(
                AnalysisPlan.status.in_([PlanStatus.DRAFT, PlanStatus.REVIEWING])
            )
            result = await db.execute(query)
            plans = list(result.scalars().all())

            if not plans:
                await self.log(LogLevel.DEBUG, "No plans in DRAFT or REVIEWING status")
                return 0

            # Filter plans by prefix if configured
            filtered_plans = self._filter_plans_by_prefix(
                plans, config["plan_prefix_filter"]
            )

            if not filtered_plans:
                await self.log(
                    LogLevel.DEBUG,
                    f"No plans matched prefix filter: {config['plan_prefix_filter']}",
                )
                return 0

            await self.log(
                LogLevel.INFO,
                f"Found {len(filtered_plans)} plan(s) matching filters",
            )

            # Process filtered plans one at a time, waiting for each to complete
            plans_processed = 0
            for plan in filtered_plans:
                # Stop processing if daemon is shutting down
                if not self.is_running:
                    break

                # Extract the integer ID value from the plan instance
                plan_id: int = int(plan.id)  # type: ignore[arg-type]
                should_process = await self._should_process_plan(
                    db, plan_id, config["auto_approve_all_changes"]
                )

                if should_process:
                    job_id = await self._create_and_wait_for_job(
                        plan_id, config["auto_approve_all_changes"]
                    )
                    if job_id:
                        plans_processed += 1

            return plans_processed

    def _filter_plans_by_prefix(
        self, plans: List[AnalysisPlan], prefix_filter: List[str]
    ) -> List[AnalysisPlan]:
        """Filter plans by name prefix."""
        if not prefix_filter:
            # If no filter configured, return all plans
            return plans

        filtered = []
        for plan in plans:
            for prefix in prefix_filter:
                if plan.name.startswith(prefix):
                    filtered.append(plan)
                    break

        return filtered

    async def _should_process_plan(
        self, db, plan_id: int, auto_approve_all: bool
    ) -> bool:
        """Check if a plan should be processed based on configuration."""
        # Build query based on configuration
        if auto_approve_all:
            # When auto_approve=True, check for APPROVED and PENDING changes (not yet APPLIED)
            count_query = select(func.count(PlanChange.id)).where(
                PlanChange.plan_id == plan_id,
                or_(
                    PlanChange.status == ChangeStatus.APPROVED,
                    PlanChange.status == ChangeStatus.PENDING,
                ),
            )
        else:
            # When auto_approve=False, only check for APPROVED changes (not yet APPLIED)
            count_query = select(func.count(PlanChange.id)).where(
                PlanChange.plan_id == plan_id,
                PlanChange.status == ChangeStatus.APPROVED,
            )

        result = await db.execute(count_query)
        unapplied_count = result.scalar_one()

        if unapplied_count == 0:
            await self.log(
                LogLevel.DEBUG,
                f"Plan {plan_id} has no changes to apply "
                f"(auto_approve={auto_approve_all})",
            )
            return False

        await self.log(
            LogLevel.INFO,
            f"Plan {plan_id} has {unapplied_count} changes to apply",
        )
        return True

    async def _create_and_wait_for_job(
        self, plan_id: int, auto_approve: bool
    ) -> Optional[str]:
        """Create a job to apply an analysis plan and wait for it to complete."""
        try:
            from app.core.dependencies import get_job_service

            job_service = get_job_service()

            # Create job metadata for applying plan
            job_metadata = {
                "plan_id": str(plan_id),
                "auto_approve": auto_approve,
                "created_by": "AUTO_PLAN_APPLIER_DAEMON",
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
                f"Created apply plan job {job_id} for plan {plan_id} "
                f"(auto_approve={auto_approve})",
            )

            # Track this job
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Apply plan {plan_id} with auto_approve={auto_approve}",
            )

            # Add to monitored jobs with plan association
            self._monitored_jobs.add(job_id)
            self._job_to_plan_mapping[job_id] = plan_id

            # Wait for the job to complete
            await self._wait_for_job_completion(job_id, plan_id)

            return job_id

        except Exception as e:
            await self.log(
                LogLevel.ERROR,
                f"Failed to create apply plan job for plan {plan_id}: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}",
            )
            return None

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
                    completed_jobs.add(job_id)
                    continue

                # Check if job has finished
                if job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    plan_id = self._job_to_plan_mapping.get(job_id)
                    await self.log(
                        LogLevel.INFO,
                        f"Apply plan job {job_id} for plan {plan_id} "
                        f"completed with status: {job.status}",
                    )

                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.FINISHED,
                        reason=f"Job completed with status {job.status}",
                    )

                    # Log any errors from the job result
                    if job.status == JobStatus.FAILED.value and job.result:
                        error_msg = job.result.get("error", "Unknown error")
                        await self.log(
                            LogLevel.ERROR,
                            f"Apply plan job {job_id} failed: {error_msg}",
                        )

                    completed_jobs.add(job_id)

        # Remove completed jobs from monitoring
        for job_id in completed_jobs:
            self._monitored_jobs.discard(job_id)
            self._job_to_plan_mapping.pop(job_id, None)

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

    async def _wait_for_job_completion(self, job_id: str, plan_id: int):
        """Wait for a specific job to complete."""
        await self.log(
            LogLevel.INFO,
            f"Waiting for apply plan job {job_id} for plan {plan_id} to complete",
        )

        config = self._load_config()
        last_heartbeat_time = time.time()

        while self.is_running and job_id in self._monitored_jobs:
            current_time = time.time()

            # Update heartbeat periodically during wait
            if current_time - last_heartbeat_time >= config["heartbeat_interval"]:
                await self.update_heartbeat()
                last_heartbeat_time = current_time

            async with AsyncSessionLocal() as db:
                job = await db.get(Job, job_id)
                if not job:
                    await self.log(
                        LogLevel.WARNING, f"Job {job_id} not found in database"
                    )
                    self._monitored_jobs.discard(job_id)
                    self._job_to_plan_mapping.pop(job_id, None)
                    break

                # Check if job has finished
                if job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    await self.log(
                        LogLevel.INFO,
                        f"Apply plan job {job_id} for plan {plan_id} "
                        f"completed with status: {job.status}",
                    )

                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.FINISHED,
                        reason=f"Job completed with status {job.status}",
                    )

                    # Log any errors from the job result
                    if job.status == JobStatus.FAILED.value and job.result:
                        error_msg = job.result.get("error", "Unknown error")
                        await self.log(
                            LogLevel.ERROR,
                            f"Apply plan job {job_id} failed: {error_msg}",
                        )

                    # Remove from monitoring
                    self._monitored_jobs.discard(job_id)
                    self._job_to_plan_mapping.pop(job_id, None)
                    break

            # Sleep a bit before checking again
            await asyncio.sleep(2)
