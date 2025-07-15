"""
Job management endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JobDetailResponse, JobResponse, JobStatus
from app.api.schemas import JobType as SchemaJobType
from app.core.dependencies import get_db, get_job_service, get_websocket_manager
from app.models import Job
from app.services.job_service import JobService
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

router = APIRouter()


def map_job_type_to_schema(model_type: str) -> str:
    """Map model JobType values to schema JobType values."""
    mapping = {
        "sync": "sync_all",
        "sync_all": "sync_all",
        "sync_scenes": "scene_sync",
        "analysis": "scene_analysis",
        "batch_analysis": "batch_analysis",
    }
    return mapping.get(model_type, model_type)


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(50, le=100, description="Maximum number of jobs to return"),
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> List[JobResponse]:
    """
    List recent jobs.

    Returns active jobs from the queue and recent completed jobs from the database.
    """
    # Get active jobs from queue
    active_jobs = await job_service.get_active_jobs(db)

    # Build database query for completed jobs
    query = select(Job)

    if status:
        query = query.where(Job.status == status)

    if job_type:
        query = query.where(Job.type == job_type)

    # Order by created_at descending and limit
    query = query.order_by(Job.created_at.desc()).limit(limit)

    # Execute query
    result = await db.execute(query)
    db_jobs = result.scalars().all()

    # Combine and convert to response models
    all_jobs = list(active_jobs) + list(db_jobs)

    # Sort by created_at and limit
    all_jobs.sort(key=lambda j: j.created_at, reverse=True)  # type: ignore[arg-type,return-value]
    all_jobs = all_jobs[:limit]

    # Convert to response models
    job_responses = []
    for job in all_jobs:
        # Ensure metadata is a dict
        metadata_dict: Dict[str, Any] = (
            job.job_metadata if isinstance(job.job_metadata, dict) else {}
        )

        job_responses.append(
            JobResponse(
                id=str(job.id),
                type=SchemaJobType(
                    map_job_type_to_schema(
                        job.type.value if hasattr(job.type, "value") else job.type
                    )
                ),
                status=JobStatus(
                    job.status.value if hasattr(job.status, "value") else job.status
                ),
                progress=float(job.progress or 0),
                parameters=metadata_dict,
                result=job.result,  # type: ignore[arg-type]
                error=job.error,  # type: ignore[arg-type]
                created_at=job.created_at,  # type: ignore[arg-type]
                updated_at=job.updated_at,  # type: ignore[arg-type]
                completed_at=job.completed_at,  # type: ignore[arg-type]
            )
        )

    return job_responses


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobDetailResponse:
    """
    Get job details.

    Checks the active queue first, then the database.
    """
    # Check active jobs first
    active_job = await job_service.get_job(job_id, db)

    if active_job:
        job: Job = active_job
    else:
        # Check database
        from app.models import Job as JobModel

        query = select(JobModel).where(JobModel.id == job_id)
        result = await db.execute(query)
        db_job = result.scalar_one_or_none()

        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )
        job = db_job

    # Get logs if available
    logs = (
        await job_service.get_job_logs(job_id, db)
        if hasattr(job_service, "get_job_logs")
        else None
    )

    # Ensure metadata is a dict
    metadata_dict: Dict[str, Any] = (
        job.job_metadata if isinstance(job.job_metadata, dict) else {}
    )

    return JobDetailResponse(
        id=str(job.id),
        type=SchemaJobType(
            map_job_type_to_schema(
                job.type.value if hasattr(job.type, "value") else job.type
            )
        ),
        status=JobStatus(
            job.status.value if hasattr(job.status, "value") else job.status
        ),
        progress=float(job.progress or 0),
        parameters=metadata_dict,
        result=job.result,  # type: ignore[arg-type]
        error=job.error,  # type: ignore[arg-type]
        created_at=job.created_at,  # type: ignore[arg-type]
        updated_at=job.updated_at,  # type: ignore[arg-type]
        completed_at=job.completed_at,  # type: ignore[arg-type]
        logs=logs,
        metadata=metadata_dict,
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cancel running job.
    """
    # Check if job is active
    active_job = await job_service.get_job(job_id, db)

    if active_job:
        # Cancel in queue
        success = await job_service.cancel_job(job_id, db)
        if success:
            return {"success": True, "message": f"Job {job_id} cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel job",
            )

    # Check database
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    # Check if job can be cancelled
    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a {job.status} job",
        )

    # Update job status
    job.status = "cancelled"  # type: ignore[assignment]
    job.error = "Cancelled by user"  # type: ignore[assignment]
    await db.commit()

    return {"success": True, "message": f"Job {job_id} cancelled successfully"}


@router.websocket("/{job_id}/ws")
async def job_progress_ws(  # type: ignore[no-untyped-def]
    websocket: WebSocket,
    job_id: str,
    manager: WebSocketManager = Depends(get_websocket_manager),
):
    """
    WebSocket for real-time job progress.
    """
    await manager.connect(websocket)

    try:
        # Subscribe to job updates
        await manager.subscribe_to_job(websocket, job_id)

        # Send current job status
        async with AsyncSession() as db:
            # Get job queue dependency
            from app.core.dependencies import get_job_service

            job_service = get_job_service()
            active_job = await job_service.get_job(job_id, db)

            if active_job:
                job: Job = active_job
            else:
                # Check database
                from app.models import Job as JobModel

                query = select(JobModel).where(JobModel.id == job_id)
                result = await db.execute(query)
                db_job = result.scalar_one_or_none()
                job = db_job  # type: ignore[assignment]

            if not job:
                await websocket.send_json(
                    {"type": "error", "message": f"Job {job_id} not found"}
                )
                await websocket.close()
                return

            # Send initial state
            status_value = (
                job.status.value if hasattr(job.status, "value") else job.status
            )
            await websocket.send_json(
                {
                    "type": "job_status",
                    "job_id": job_id,
                    "status": status_value,
                    "progress": job.progress or 0,
                    "message": (
                        job.job_metadata.get("last_message")
                        if isinstance(job.job_metadata, dict)
                        else None
                    ),
                    "result": job.result,
                    "error": job.error,
                }
            )

        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_json()

                # Handle ping/pong
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await manager.disconnect(websocket)
        await manager.unsubscribe_from_job(websocket, job_id)


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retry a failed or cancelled job.
    """
    # Get the original job from database
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    # Check if job can be retried
    if job.status not in ["failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry a {job.status} job",
        )

    # Get job metadata
    metadata_dict: Dict[str, Any] = (
        job.job_metadata if isinstance(job.job_metadata, dict) else {}
    )

    # Create a new job with the same parameters
    new_job_id = await job_service.create_job(
        job_type=job.type,  # type: ignore[arg-type]
        parameters=metadata_dict,
        db=db,
    )

    # Start the job
    success = await job_service.start_job(new_job_id, db)

    if success:
        return {
            "success": True,
            "message": f"Job {job_id} retried as new job {new_job_id}",
            "new_job_id": new_job_id,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry job",
        )
