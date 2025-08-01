from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import String, and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus, JobType


class JobRepository:
    """Repository for job persistence and retrieval."""

    async def create_job(
        self,
        job_id: str,
        job_type: JobType,
        db: Union[Session, AsyncSession],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Create job record in database."""
        job = Job(
            id=job_id,
            type=job_type.value,  # Pass the string value since we're using explicit enum values
            status=JobStatus.PENDING.value,  # Pass the string value
            progress=0,
            job_metadata=metadata or {},
        )
        db.add(job)
        if isinstance(db, AsyncSession):
            await db.commit()
            await db.refresh(job)
        else:
            db.commit()
            db.refresh(job)
        return job

    async def _fetch_job(
        self, job_id: str, db: Union[Session, AsyncSession]
    ) -> Optional[Job]:
        """Fetch job by ID from database."""
        if isinstance(db, AsyncSession):
            result = await db.execute(select(Job).filter(Job.id == job_id))
            return result.scalar_one_or_none()
        return db.query(Job).filter(Job.id == job_id).first()

    def _update_job_fields(
        self,
        job: Job,
        status: JobStatus,
        progress: Optional[int],
        result: Optional[Dict[str, Any]],
        error: Optional[str],
        message: Optional[str],
    ) -> None:
        """Update job fields based on provided values."""
        import logging

        logger = logging.getLogger(__name__)

        job.status = status.value if hasattr(status, "value") else status  # type: ignore[assignment]

        if progress is not None:
            job.progress = progress  # type: ignore[assignment]
        if result is not None:
            job.result = result  # type: ignore[assignment]
            # Extract processed_items from result if available
            if isinstance(result, dict) and "processed_items" in result:
                job.processed_items = result["processed_items"]  # type: ignore[assignment]
                logger.debug(
                    f"Updated job {job.id} processed_items to {result['processed_items']}"
                )
            # Also extract total_items if available
            if isinstance(result, dict) and "total_items" in result:
                job.total_items = result["total_items"]  # type: ignore[assignment]
        if error is not None:
            job.error = error  # type: ignore[assignment]
        if message is not None:
            if not job.job_metadata:
                job.job_metadata = {}  # type: ignore[assignment]
            # Log current metadata before update
            logger.debug(
                f"Job {job.id} metadata before message update: {job.job_metadata}"
            )
            # Update metadata in place to avoid losing existing values
            job.job_metadata["last_message"] = message
            # Mark the JSON column as modified so SQLAlchemy tracks the change
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(job, "job_metadata")
            logger.debug(
                f"Job {job.id} metadata after message update: {job.job_metadata}"
            )

    def _update_job_timestamps(self, job: Job, status: JobStatus) -> None:
        """Update job timestamps based on status."""
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()  # type: ignore[assignment]
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()  # type: ignore[assignment]
        job.updated_at = datetime.utcnow()  # type: ignore[assignment]

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        db: Union[Session, AsyncSession],
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status and related fields."""
        job = await self._fetch_job(job_id, db)
        if not job:
            return None

        self._update_job_fields(job, status, progress, result, error, message)
        self._update_job_timestamps(job, status)

        if isinstance(db, AsyncSession):
            await db.commit()
            await db.refresh(job)
        else:
            db.commit()
            db.refresh(job)
        return job

    async def get_job(
        self, job_id: str, db: Union[Session, AsyncSession]
    ) -> Optional[Job]:
        """Get job by ID."""
        if isinstance(db, AsyncSession):
            result = await db.execute(select(Job).filter(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                # Ensure we have the latest metadata by expiring the object
                await db.refresh(job)
            return job
        else:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                db.refresh(job)
            return job

    async def list_jobs(
        self,
        db: Union[Session, AsyncSession],
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """List jobs with optional filters."""
        if isinstance(db, AsyncSession):
            query = select(Job)

            if status:
                query = query.filter(Job.status == status)

            if job_type:
                query = query.filter(Job.type == job_type)

            query = query.order_by(desc(Job.created_at)).offset(offset).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())
        else:
            query = db.query(Job)  # type: ignore

            if status:
                query = query.filter(Job.status == status)

            if job_type:
                query = query.filter(Job.type == job_type)

            return list(
                query.order_by(desc(Job.created_at)).offset(offset).limit(limit).all()  # type: ignore[attr-defined]
            )

    async def cancel_job(
        self, job_id: str, db: Union[Session, AsyncSession]
    ) -> Optional[Job]:
        """Cancel a job by updating its status."""
        return await self.update_job_status(
            job_id=job_id,
            status=JobStatus.CANCELLED,
            db=db,
            message="Job cancelled by user",
        )

    async def get_active_jobs(
        self, db: Union[Session, AsyncSession], job_type: Optional[JobType] = None
    ) -> List[Job]:
        """Get all active (pending or running) jobs."""
        if isinstance(db, AsyncSession):
            query = select(Job).filter(
                Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
            )

            if job_type:
                query = query.filter(Job.type == job_type)

            query = query.order_by(Job.created_at)
            result = await db.execute(query)
            return list(result.scalars().all())
        else:
            query = db.query(Job).filter(  # type: ignore
                Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
            )

            if job_type:
                query = query.filter(Job.type == job_type)

            return list(query.order_by(Job.created_at).all())  # type: ignore[attr-defined]

    async def cleanup_old_jobs(
        self, db: Union[Session, AsyncSession], days: int = 30
    ) -> int:
        """Clean up completed jobs older than specified days."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        if isinstance(db, AsyncSession):
            from sqlalchemy import delete

            stmt = delete(Job).filter(
                Job.status.in_(
                    [
                        JobStatus.COMPLETED.value,
                        JobStatus.FAILED.value,
                        JobStatus.CANCELLED.value,
                    ]
                ),
                Job.completed_at < cutoff_date,
            )
            result = await db.execute(stmt)
            deleted_count = result.rowcount
            await db.commit()
        else:
            deleted_count = (
                db.query(Job)
                .filter(
                    Job.status.in_(
                        [
                            JobStatus.COMPLETED.value,
                            JobStatus.FAILED.value,
                            JobStatus.CANCELLED.value,
                        ]
                    ),
                    Job.completed_at < cutoff_date,
                )
                .delete()
            )
            db.commit()
        return deleted_count

    async def get_all_active_job_scene_ids(self, db: AsyncSession) -> List[str]:
        """Get all scene IDs that have active jobs."""
        # Query for jobs that are active and have scene_ids in their metadata
        query = select(Job).filter(
            and_(
                Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
                # Cast JSON to text and check if it contains "scene_ids"
                func.cast(Job.job_metadata, String).contains('"scene_ids"'),
            )
        )

        result = await db.execute(query)
        jobs = result.scalars().all()

        # Collect all unique scene IDs from active jobs
        all_scene_ids = set()
        for job in jobs:
            if job.job_metadata and "scene_ids" in job.job_metadata:
                job_scene_ids = job.job_metadata.get("scene_ids", [])
                if isinstance(job_scene_ids, list):
                    all_scene_ids.update(job_scene_ids)

        return list(all_scene_ids)

    async def get_active_jobs_for_scenes(
        self, scene_ids: List[str], db: AsyncSession
    ) -> Dict[str, List[Job]]:
        """Get active jobs (pending/running) for multiple scenes."""
        if not scene_ids:
            return {}

        # Query for jobs that are active and have scene_ids in their metadata
        # Use JSON cast to check if metadata contains scene_ids key
        query = select(Job).filter(
            and_(
                Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
                # Cast JSON to text and check if it contains "scene_ids"
                func.cast(Job.job_metadata, String).contains('"scene_ids"'),
            )
        )

        result = await db.execute(query)
        jobs = result.scalars().all()

        # Group jobs by scene_id
        scene_jobs: Dict[str, List[Job]] = {}
        for job in jobs:
            if job.job_metadata and "scene_ids" in job.job_metadata:
                job_scene_ids = job.job_metadata.get("scene_ids", [])
                if isinstance(job_scene_ids, list):
                    for scene_id in job_scene_ids:
                        if scene_id in scene_ids:
                            if scene_id not in scene_jobs:
                                scene_jobs[scene_id] = []
                            scene_jobs[scene_id].append(job)

        return scene_jobs

    async def get_recent_jobs_for_scenes(
        self, scene_ids: List[str], db: AsyncSession, hours: int = 24
    ) -> Dict[str, List[Job]]:
        """Get recently completed jobs for multiple scenes."""
        if not scene_ids:
            return {}

        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Query for completed jobs within the time window
        query = select(Job).filter(
            and_(
                Job.status == JobStatus.COMPLETED.value,
                Job.completed_at >= cutoff_time,
                # Cast JSON to text and check if it contains "scene_ids"
                func.cast(Job.job_metadata, String).contains('"scene_ids"'),
            )
        )

        result = await db.execute(query)
        jobs = result.scalars().all()

        # Group jobs by scene_id
        scene_jobs: Dict[str, List[Job]] = {}
        for job in jobs:
            if job.job_metadata and "scene_ids" in job.job_metadata:
                job_scene_ids = job.job_metadata.get("scene_ids", [])
                if isinstance(job_scene_ids, list):
                    for scene_id in job_scene_ids:
                        if scene_id in scene_ids:
                            if scene_id not in scene_jobs:
                                scene_jobs[scene_id] = []
                            scene_jobs[scene_id].append(job)

        return scene_jobs


# Global instance
job_repository = JobRepository()
