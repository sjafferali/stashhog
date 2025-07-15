import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tasks import TaskStatus, get_task_queue
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import job_repository
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class JobService:
    """Service to manage jobs and coordinate with task queue."""

    def __init__(self) -> None:
        self.job_handlers: Dict[JobType, Callable] = {}

    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler function for a specific job type."""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")

    async def create_job(
        self,
        job_type: JobType,
        db: Union[Session, AsyncSession],
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Job:
        """Create a new job and queue it for execution."""
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Create job in database
        job = await job_repository.create_job(
            job_id=job_id, job_type=job_type, db=db, metadata=metadata
        )

        # Get handler for job type
        handler = self.job_handlers.get(job_type)
        if not handler:
            await job_repository.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                db=db,
                error=f"No handler registered for job type: {job_type.value}",
            )
            raise ValueError(f"No handler registered for job type: {job_type.value}")

        # Create task wrapper with progress callback
        async def task_wrapper() -> str:
            try:
                # Update job status to running
                await self._update_job_status(
                    job_id=job_id, status=JobStatus.RUNNING, message="Job started"
                )

                # Execute handler with job context
                result = await handler(
                    job_id=job_id,
                    progress_callback=lambda progress, message=None: self._update_job_progress(
                        job_id, progress, message
                    ),
                    **kwargs,
                )

                # Update job status to completed
                await self._update_job_status(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    progress=100,
                    result=result,
                    message="Job completed successfully",
                )

                return str(result) if result is not None else ""

            except Exception as e:
                logger.error(f"Job {job_id} failed: {str(e)}")
                await self._update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=str(e),
                    message=f"Job failed: {str(e)}",
                )
                raise

        # Queue the task
        task_queue = get_task_queue()
        task_id = await task_queue.submit(
            func=task_wrapper,
            name=f"{job_type.value}_{job_id}",
        )

        # Store task ID in job metadata
        if job.metadata is None:
            job.metadata = {}
        job.metadata = {**job.metadata, "task_id": task_id}
        if hasattr(db, "commit"):
            db.commit()
        else:
            await db.commit()  # type: ignore[misc]

        logger.info(f"Created job {job_id} of type {job_type.value}")
        return job

    async def get_job(
        self, job_id: str, db: Union[Session, AsyncSession]
    ) -> Optional[Job]:
        """Get job by ID."""
        return await job_repository.get_job(job_id, db)

    async def list_jobs(
        self,
        db: Union[Session, AsyncSession],
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """List jobs with optional filters."""
        return await job_repository.list_jobs(
            db=db, status=status, job_type=job_type, limit=limit, offset=offset
        )

    async def cancel_job(self, job_id: str, db: Union[Session, AsyncSession]) -> bool:
        """Cancel a running job."""
        job = await job_repository.get_job(job_id, db)
        if not job:
            return False

        # Cancel task if running
        if job.metadata is not None and "task_id" in job.metadata:
            task_id = job.metadata["task_id"]
            task_queue = get_task_queue()
            await task_queue.cancel_task(task_id)

        # Update job status
        await job_repository.cancel_job(job_id, db)

        # Send WebSocket notification
        await self._send_job_update(
            job_id, {"status": JobStatus.CANCELLED.value, "message": "Job cancelled"}
        )

        logger.info(f"Cancelled job {job_id}")
        return True

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Update job status in database and send WebSocket notification."""
        db = next(get_db())
        try:
            job = await job_repository.update_job_status(
                job_id=job_id,
                status=status,
                db=db,
                progress=progress,
                result=result,
                error=error,
                message=message,
            )

            if job:
                # Send WebSocket update
                await self._send_job_update(
                    job_id,
                    {
                        "status": status.value,
                        "progress": job.progress,
                        "message": message,
                        "error": error,
                        "result": result,
                    },
                )
        finally:
            db.close()

    async def _update_job_progress(
        self, job_id: str, progress: int, message: Optional[str] = None
    ) -> None:
        """Update job progress."""
        await self._update_job_status(
            job_id=job_id, status=JobStatus.RUNNING, progress=progress, message=message
        )

    async def _send_job_update(self, job_id: str, data: Dict[str, Any]) -> None:
        """Send job update via WebSocket."""
        await websocket_manager.broadcast_json(
            {
                "type": "job_update",
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat(),
                **data,
            }
        )

    def _task_callback(
        self,
        job_id: str,
        status: TaskStatus,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """Callback for task status updates."""
        # Task status is already handled in task_wrapper
        # This is mainly for logging
        logger.debug(f"Task callback for job {job_id}: status={status}")

    async def get_active_jobs(
        self, db: Union[Session, AsyncSession], job_type: Optional[JobType] = None
    ) -> List[Job]:
        """Get all active jobs."""
        return await job_repository.get_active_jobs(db, job_type)

    async def cleanup_old_jobs(
        self, db: Union[Session, AsyncSession], days: int = 30
    ) -> int:
        """Clean up old completed jobs."""
        count = await job_repository.cleanup_old_jobs(db, days)
        logger.info(f"Cleaned up {count} old jobs")
        return count


# Global instance
job_service = JobService()
