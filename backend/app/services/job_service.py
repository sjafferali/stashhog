import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cancellation import cancellation_manager
from app.core.tasks import TaskStatus, get_task_queue
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import job_repository
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class JobService:
    """Service to manage jobs and coordinate with task queue."""

    def __init__(self) -> None:
        self.job_handlers: dict[JobType, Callable] = {}
        # Locks for each job type to prevent concurrent execution
        self.job_type_locks: dict[JobType, asyncio.Lock] = {}
        # Track which jobs should use mutual exclusion
        self.sync_job_types = {
            JobType.SYNC,
            JobType.SYNC_ALL,
            JobType.SYNC_SCENES,
            JobType.SYNC_PERFORMERS,
            JobType.SYNC_TAGS,
            JobType.SYNC_STUDIOS,
            JobType.ANALYSIS,
            JobType.APPLY_PLAN,
            JobType.GENERATE_DETAILS,
        }

    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler function for a specific job type."""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")

    async def create_job(
        self,
        job_type: JobType,
        db: Union[Session, AsyncSession],
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Job:
        """Create a new job and queue it for execution."""
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Create cancellation token for this job
        cancellation_manager.create_token(job_id)

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

        # Get or create lock for this job type if it's a sync job
        job_lock = None
        if job_type in self.sync_job_types:
            if job_type not in self.job_type_locks:
                self.job_type_locks[job_type] = asyncio.Lock()
            job_lock = self.job_type_locks[job_type]

        # Create task wrapper with progress callback
        async def task_wrapper() -> str:
            from app.core.database import AsyncSessionLocal

            # Acquire lock if this is a sync job
            if job_lock:
                logger.info(f"Job {job_id} ({job_type.value}) waiting for lock...")

                # Check if lock is already held
                if job_lock.locked():
                    # Update job status to indicate waiting
                    async with AsyncSessionLocal() as wait_db:
                        await self._update_job_status_with_session(
                            job_id=job_id,
                            status=JobStatus.PENDING,
                            message=f"Waiting for another {job_type.value} job to complete",
                            db=wait_db,
                        )
                        await wait_db.commit()

                async with job_lock:
                    logger.info(f"Job {job_id} ({job_type.value}) acquired lock")
                    return await self._execute_job_with_lock(
                        job_id, job_type, handler, metadata, kwargs
                    )
            else:
                # Non-sync jobs don't need locks
                return await self._execute_job_with_lock(
                    job_id, job_type, handler, metadata, kwargs
                )

        # Queue the task
        task_queue = get_task_queue()
        task_id = await task_queue.submit(
            func=task_wrapper,
            name=f"{job_type.value}_{job_id}",
        )

        # Store task ID in job metadata
        if job.job_metadata is None:
            job.job_metadata = {}
        job.job_metadata = {**job.job_metadata, "task_id": task_id}  # type: ignore[assignment]
        await db.commit()  # type: ignore[misc]

        logger.info(f"Created job {job_id} of type {job_type.value}")
        return job

    async def _execute_job_with_lock(
        self,
        job_id: str,
        job_type: JobType,
        handler: Callable,
        metadata: Optional[dict[str, Any]],
        kwargs: dict[str, Any],
    ) -> str:
        """Execute a job with proper status updates."""
        from app.core.database import AsyncSessionLocal

        try:
            # Create a single database session for all job status updates
            async with AsyncSessionLocal() as status_db:
                # Update job status to running
                await self._update_job_status_with_session(
                    job_id=job_id,
                    status=JobStatus.RUNNING,
                    message="Job started",
                    db=status_db,
                )
                await status_db.commit()

            # Merge job metadata with kwargs for handlers that expect direct parameters
            handler_kwargs = kwargs.copy()
            if metadata:
                handler_kwargs.update(metadata)

            # Get cancellation token
            cancellation_token = cancellation_manager.get_token(job_id)

            # Create an async progress callback that uses its own session
            async def async_progress_callback(
                progress: int, message: Optional[str] = None
            ) -> None:
                # Use _update_job_progress which parses the message for counts
                await self._update_job_progress(job_id, progress, message)

            # Execute handler with job context
            result = await handler(
                job_id=job_id,
                progress_callback=async_progress_callback,
                cancellation_token=cancellation_token,
                **handler_kwargs,
            )

            # Update job status based on result
            async with AsyncSessionLocal() as final_db:
                # Check if result indicates failure
                job_status = JobStatus.COMPLETED
                message = "Job completed successfully"

                if isinstance(result, dict):
                    result_status = result.get("status", "completed")
                    if result_status == "failed":
                        job_status = JobStatus.FAILED
                        message = "Job failed with errors"
                    elif result_status == "completed_with_errors":
                        # Still mark as completed but note the errors in the message
                        errors = result.get("errors", [])
                        error_count = len(errors)
                        message = f"Job completed with {error_count} error(s)"

                await self._update_job_status_with_session(
                    job_id=job_id,
                    status=job_status,
                    progress=100,
                    result=result,
                    message=message,
                    db=final_db,
                )
                await final_db.commit()

            return str(result) if result is not None else ""

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            # Update status in a new session for cancellation
            async with AsyncSessionLocal() as cancel_db:
                await self._update_job_status_with_session(
                    job_id=job_id,
                    status=JobStatus.CANCELLED,
                    error="Job was cancelled by user",
                    message="Job cancelled",
                    db=cancel_db,
                )
                await cancel_db.commit()
            raise
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            # Update status in a new session for error case
            async with AsyncSessionLocal() as error_db:
                await self._update_job_status_with_session(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=str(e),
                    message=f"Job failed: {str(e)}",
                    db=error_db,
                )
                await error_db.commit()
            raise
        finally:
            # Clean up cancellation token
            cancellation_manager.remove_token(job_id)

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
    ) -> list[Job]:
        """List jobs with optional filters."""
        return await job_repository.list_jobs(
            db=db, status=status, job_type=job_type, limit=limit, offset=offset
        )

    async def cancel_job(self, job_id: str, db: Union[Session, AsyncSession]) -> bool:
        """Cancel a running job."""
        job = await job_repository.get_job(job_id, db)
        if not job:
            return False

        # Cancel using cancellation token
        cancellation_manager.cancel_job(job_id)

        # Cancel task if running
        if job.job_metadata is not None and "task_id" in job.job_metadata:
            task_id = str(job.job_metadata["task_id"])
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

    async def _update_job_status_with_session(
        self,
        job_id: str,
        status: JobStatus,
        db: AsyncSession,
        progress: Optional[int] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Update job status using provided database session."""
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
            # Send WebSocket update with the job object to avoid re-fetching
            await self._send_job_update(
                job_id,
                {
                    "status": status.value,
                    "progress": job.progress,
                    "message": message,
                    "error": error,
                    "result": result,
                },
                job=job,  # Pass the job to avoid double-fetch
            )

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Update job status in database and send WebSocket notification."""
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await self._update_job_status_with_session(
                job_id=job_id,
                status=status,
                db=db,
                progress=progress,
                result=result,
                error=error,
                message=message,
            )

    async def _update_job_progress(
        self, job_id: str, progress: int, message: Optional[str] = None
    ) -> None:
        """Update job progress."""
        # Extract processed/total from message if present
        processed_items = None
        total_items = None

        if message and "Processed" in message and "/" in message:
            # Parse messages like "Processed 4/6 scenes"
            import re

            match = re.search(r"Processed (\d+)/(\d+)", message)
            if match:
                processed_items = int(match.group(1))
                total_items = int(match.group(2))

        # Update job with progress and counts
        await self._update_job_status_with_counts(
            job_id=job_id,
            status=JobStatus.RUNNING,
            progress=progress,
            message=message,
            processed_items=processed_items,
            total_items=total_items,
        )

    async def _update_job_status_with_counts(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
        processed_items: Optional[int] = None,
        total_items: Optional[int] = None,
    ) -> None:
        """Update job status with item counts in database and send WebSocket notification."""
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            job = await job_repository.get_job(job_id, db)
            if job:
                # Update standard fields
                job.status = status.value if hasattr(status, "value") else status  # type: ignore[assignment]

                if progress is not None:
                    job.progress = progress  # type: ignore[assignment]
                if result is not None:
                    job.result = result  # type: ignore[assignment]
                if error is not None:
                    job.error = error  # type: ignore[assignment]

                # Update item counts
                if processed_items is not None:
                    job.processed_items = processed_items  # type: ignore[assignment]
                if total_items is not None:
                    job.total_items = total_items  # type: ignore[assignment]

                # Update timestamps based on status
                if status == JobStatus.RUNNING and not job.started_at:
                    from datetime import datetime

                    job.started_at = datetime.utcnow()  # type: ignore[assignment]
                elif status in [
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ]:
                    from datetime import datetime

                    job.completed_at = datetime.utcnow()  # type: ignore[assignment]

                await db.commit()

                # Force read the latest metadata from DB to avoid stale data
                await db.refresh(job)

                # Re-fetch to ensure we have the absolute latest data (including any concurrent updates)
                fresh_job = await job_repository.get_job(job_id, db)
                if fresh_job:
                    job = fresh_job

                # Build the complete job data from the current job object
                metadata_dict: Dict[str, Any] = (
                    job.job_metadata if isinstance(job.job_metadata, dict) else {}
                )

                job_data = {
                    "id": job.id,
                    "type": job.type.value if hasattr(job.type, "value") else job.type,
                    "status": (
                        job.status.value if hasattr(job.status, "value") else job.status
                    ),
                    "progress": job.progress,
                    "total": job.total_items,
                    "processed_items": job.processed_items,
                    "parameters": metadata_dict,  # Frontend expects metadata as parameters
                    "metadata": metadata_dict,  # Also include as metadata for compatibility
                    "result": job.result,
                    "error": job.error,
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else None
                    ),
                    "updated_at": (
                        job.updated_at.isoformat() if job.updated_at else None
                    ),
                    "started_at": (
                        job.started_at.isoformat() if job.started_at else None
                    ),
                    "completed_at": (
                        job.completed_at.isoformat() if job.completed_at else None
                    ),
                }

                # Send WebSocket update directly with the current job data
                logger.debug(f"Broadcasting job update with metadata: {metadata_dict}")
                await websocket_manager.broadcast_job_update(job_data)

    async def _send_job_update(
        self, job_id: str, data: dict[str, Any], job: Optional[Job] = None
    ) -> None:
        """Send job update via WebSocket.

        Args:
            job_id: Job ID
            data: Additional data to include
            job: Optional job object to use (avoids re-fetching from DB)
        """
        logger.debug(f"Sending job update for {job_id} with data: {data}")

        # If job not provided, fetch from database
        if job is None:
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                job = await job_repository._fetch_job(job_id, db)

        if job:
            # Ensure metadata is a dict
            metadata_dict: dict[str, Any] = (
                job.job_metadata if isinstance(job.job_metadata, dict) else {}
            )

            job_data = {
                "id": job.id,
                "type": job.type.value if hasattr(job.type, "value") else job.type,
                "status": (
                    job.status.value if hasattr(job.status, "value") else job.status
                ),
                "progress": job.progress,
                "total": job.total_items,
                "processed_items": job.processed_items,
                "parameters": metadata_dict,  # Frontend expects metadata as parameters
                "metadata": metadata_dict,  # Also include as metadata for compatibility
                "result": job.result,
                "error": job.error,
                "created_at": (job.created_at.isoformat() if job.created_at else None),
                "updated_at": (job.updated_at.isoformat() if job.updated_at else None),
                "started_at": (job.started_at.isoformat() if job.started_at else None),
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
            }
            logger.debug(f"Broadcasting job update with metadata: {metadata_dict}")
            await websocket_manager.broadcast_job_update(job_data)

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
    ) -> list[Job]:
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
