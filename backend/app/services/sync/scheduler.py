import logging
from datetime import datetime
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.models import Job, JobStatus, JobType, ScheduledTask
from app.services.stash_service import StashService

from .sync_service import SyncService

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Manages scheduled sync operations"""

    def __init__(self, scheduler: Optional[AsyncIOScheduler] = None):
        self.scheduler = scheduler or AsyncIOScheduler()
        self._jobs: Dict[str, Any] = {}

    def start(self) -> None:
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Sync scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Sync scheduler stopped")

    def schedule_full_sync(
        self, cron_expression: str, job_id: str = "full_sync", force: bool = False
    ) -> str:
        """
        Schedule regular full sync using cron expression

        Args:
            cron_expression: Cron expression (e.g., "0 2 * * *" for 2 AM daily)
            job_id: Unique job identifier
            force: Force full sync ignoring timestamps

        Returns:
            Job ID
        """
        # Parse cron expression
        try:
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                raise ValueError("Invalid cron expression")

            trigger = CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4],
            )
        except Exception as e:
            logger.error(f"Invalid cron expression: {cron_expression} - {str(e)}")
            raise

        # Remove existing job if any
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)

        # Add new job
        job = self.scheduler.add_job(
            self._run_full_sync,
            trigger=trigger,
            id=job_id,
            kwargs={"force": force},
            replace_existing=True,
            misfire_grace_time=3600,  # 1 hour grace time
        )

        self._jobs[job_id] = job
        logger.info(f"Scheduled full sync with cron: {cron_expression}")

        return job_id

    def schedule_incremental_sync(
        self, interval_minutes: int, job_id: str = "incremental_sync"
    ) -> str:
        """
        Schedule incremental sync at regular intervals

        Args:
            interval_minutes: Interval in minutes between syncs
            job_id: Unique job identifier

        Returns:
            Job ID
        """
        if interval_minutes < 5:
            raise ValueError("Minimum interval is 5 minutes")

        # Remove existing job if any
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)

        # Add new job
        job = self.scheduler.add_job(
            self._run_incremental_sync,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,  # 5 minutes grace time
        )

        self._jobs[job_id] = job
        logger.info(f"Scheduled incremental sync every {interval_minutes} minutes")

        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job

        Args:
            job_id: Job ID to cancel

        Returns:
            True if job was cancelled
        """
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"Cancelled scheduled job: {job_id}")
            return True
        return False

    def get_scheduled_jobs(self) -> Dict[str, Any]:
        """Get information about scheduled jobs"""
        jobs_info = {}

        for job_id, job in self._jobs.items():
            next_run = job.next_run_time
            jobs_info[job_id] = {
                "id": job_id,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger),
                "active": job.next_run_time is not None,
            }

        return jobs_info

    async def _run_full_sync(self, force: bool = False) -> None:
        """Execute full sync job"""
        from uuid import uuid4

        from app.core.config import get_settings
        from app.core.database import SessionLocal

        try:
            with SessionLocal() as db:
                # Create job record
                job_id = str(uuid4())
                job = Job(
                    id=job_id,
                    type=JobType.SYNC_ALL.value,
                    status=JobStatus.RUNNING.value,
                    metadata={"force": force, "scheduled": True},
                    created_at=datetime.utcnow(),
                )
                db.add(job)
                db.commit()

                # Run sync
                settings = get_settings()
                stash_service = StashService(
                    stash_url=settings.stash.url, api_key=settings.stash.api_key
                )
                sync_service = SyncService(stash_service, db)

                result = await sync_service.sync_all(job_id=job_id, force=force)

                # Update job
                job.status = JobStatus.COMPLETED  # type: ignore[assignment]
                job.completed_at = datetime.utcnow()  # type: ignore[assignment]
                job.result = {  # type: ignore[assignment]
                    "total_items": result.total_items,
                    "processed_items": result.processed_items,
                    "created_items": result.created_items,
                    "updated_items": result.updated_items,
                    "failed_items": result.failed_items,
                }
                db.commit()

                # Update scheduled task
                self._update_scheduled_task(db, "full_sync", "completed")

        except Exception as e:
            logger.error(f"Scheduled full sync failed: {str(e)}")
            self._update_scheduled_task(db, "full_sync", "failed", str(e))

    async def _run_incremental_sync(self) -> None:
        """Execute incremental sync job"""
        from uuid import uuid4

        from app.core.config import get_settings
        from app.core.database import SessionLocal

        try:
            with SessionLocal() as db:
                # Create job record
                job_id = str(uuid4())
                job = Job(
                    id=job_id,
                    type=JobType.SYNC_SCENES.value,
                    status=JobStatus.RUNNING.value,
                    metadata={"incremental": True, "scheduled": True},
                    created_at=datetime.utcnow(),
                )
                db.add(job)
                db.commit()

                # Run sync
                settings = get_settings()
                stash_service = StashService(
                    stash_url=settings.stash.url, api_key=settings.stash.api_key
                )
                sync_service = SyncService(stash_service, db)

                # Get last sync time
                last_sync = await sync_service._get_last_sync_time("scene")

                result = await sync_service.sync_scenes(since=last_sync, job_id=job_id)

                # Update job
                job.status = JobStatus.COMPLETED  # type: ignore[assignment]
                job.completed_at = datetime.utcnow()  # type: ignore[assignment]
                job.result = {  # type: ignore[assignment]
                    "scenes_processed": result.stats.scenes_processed,
                    "scenes_created": result.stats.scenes_created,
                    "scenes_updated": result.stats.scenes_updated,
                    "scenes_failed": result.stats.scenes_failed,
                }
                db.commit()

                # Update scheduled task
                self._update_scheduled_task(db, "incremental_sync", "completed")

        except Exception as e:
            logger.error(f"Scheduled incremental sync failed: {str(e)}")
            self._update_scheduled_task(db, "incremental_sync", "failed", str(e))

    def _update_scheduled_task(
        self, db: Session, task_name: str, status: str, error: Optional[str] = None
    ) -> None:
        """Update scheduled task record"""
        task = db.query(ScheduledTask).filter(ScheduledTask.name == task_name).first()

        if task:
            task.last_run = datetime.utcnow()  # type: ignore[assignment]
            # Store status and error in config
            if task.config is None:
                task.config = {}
            task.config["last_status"] = status
            task.config["error_message"] = error

            # Calculate next run
            if task_name in self._jobs:
                job = self._jobs[task_name]
                if job.next_run_time:
                    task.next_run = job.next_run_time

            db.commit()


# Global scheduler instance
sync_scheduler = SyncScheduler()
