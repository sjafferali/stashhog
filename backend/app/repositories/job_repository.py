from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import desc, select
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
            type=job_type,  # Pass the enum object, not the string value
            status=JobStatus.PENDING,  # Pass the enum object, not the string value
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
        job.status = status.value if hasattr(status, "value") else status  # type: ignore[assignment]

        if progress is not None:
            job.progress = progress  # type: ignore[assignment]
        if result is not None:
            job.result = result  # type: ignore[assignment]
        if error is not None:
            job.error = error  # type: ignore[assignment]
        if message is not None:
            if not job.job_metadata:
                job.job_metadata = {}  # type: ignore[assignment]
            job.job_metadata = {**job.job_metadata, "last_message": message}  # type: ignore[assignment]

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
            return result.scalar_one_or_none()
        else:
            return db.query(Job).filter(Job.id == job_id).first()

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


# Global instance
job_repository = JobRepository()
