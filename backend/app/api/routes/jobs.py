"""
Job management endpoints.
"""
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, Query, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.schemas import (
    JobResponse,
    JobDetailResponse,
    JobStatus,
    JobType
)
from app.core.dependencies import get_db, get_job_queue, get_websocket_manager
from app.services.job_queue import JobQueue
from app.services.websocket_manager import WebSocketManager
from app.models import Job

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(50, le=100, description="Maximum number of jobs to return"),
    db: AsyncSession = Depends(get_db),
    job_queue: JobQueue = Depends(get_job_queue)
) -> List[JobResponse]:
    """
    List recent jobs.
    
    Returns active jobs from the queue and recent completed jobs from the database.
    """
    # Get active jobs from queue
    active_jobs = await job_queue.get_active_jobs()
    
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
    all_jobs = active_jobs + db_jobs
    
    # Sort by created_at and limit
    all_jobs.sort(key=lambda j: j.created_at, reverse=True)
    all_jobs = all_jobs[:limit]
    
    # Convert to response models
    job_responses = []
    for job in all_jobs:
        job_responses.append(JobResponse(
            id=job.id,
            type=JobType(job.type),
            status=JobStatus(job.status),
            progress=job.progress or 0,
            parameters=job.metadata or {},
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at
        ))
    
    return job_responses


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    job_queue: JobQueue = Depends(get_job_queue)
) -> JobDetailResponse:
    """
    Get job details.
    
    Checks the active queue first, then the database.
    """
    # Check active jobs first
    active_job = await job_queue.get_job(job_id)
    
    if active_job:
        job = active_job
    else:
        # Check database
        from app.models import Job as JobModel
        query = select(JobModel).where(JobModel.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
    
    # Get logs if available
    logs = await job_queue.get_job_logs(job_id) if hasattr(job_queue, 'get_job_logs') else None
    
    return JobDetailResponse(
        id=job.id,
        type=JobType(job.type),
        status=JobStatus(job.status),
        progress=job.progress or 0,
        parameters=job.metadata or {},
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        logs=logs,
        metadata=job.metadata
    )


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    job_queue: JobQueue = Depends(get_job_queue),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Cancel running job.
    """
    # Check if job is active
    active_job = await job_queue.get_job(job_id)
    
    if active_job:
        # Cancel in queue
        success = await job_queue.cancel_job(job_id)
        if success:
            return {
                "success": True,
                "message": f"Job {job_id} cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel job"
            )
    
    # Check database
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check if job can be cancelled
    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a {job.status} job"
        )
    
    # Update job status
    job.status = "cancelled"
    job.error = "Cancelled by user"
    await db.commit()
    
    return {
        "success": True,
        "message": f"Job {job_id} cancelled successfully"
    }




@router.websocket("/{job_id}/ws")
async def job_progress_ws(
    websocket: WebSocket,
    job_id: str,
    manager: WebSocketManager = Depends(get_websocket_manager)
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
            from app.core.dependencies import get_job_queue
            job_queue = get_job_queue()
            active_job = await job_queue.get_job(job_id)
            
            if active_job:
                job = active_job
            else:
                # Check database
                from app.models import Job as JobModel
                query = select(JobModel).where(JobModel.id == job_id)
                result = await db.execute(query)
                job = result.scalar_one_or_none()
            
            if not job:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Job {job_id} not found"
                })
                await websocket.close()
                return
            
            # Send initial state
            await websocket.send_json({
                "type": "job_status",
                "job_id": job_id,
                "status": job.status,
                "progress": job.progress or 0,
                "message": job.metadata.get("last_message") if job.metadata else None,
                "result": job.result,
                "error": job.error
            })
        
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
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await manager.disconnect(websocket)
        await manager.unsubscribe_from_job(websocket, job_id)