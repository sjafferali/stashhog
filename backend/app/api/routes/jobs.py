"""
Job management endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JobDetailResponse, JobResponse, JobsListResponse, JobStatus
from app.api.schemas import JobType as SchemaJobType
from app.core.dependencies import get_db, get_job_service, get_websocket_manager
from app.core.job_registry import get_job_type_mapping, to_api_response
from app.models import Job
from app.models.handled_download import HandledDownload
from app.services.job_service import JobService
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metadata")
async def get_job_metadata() -> Dict[str, Any]:
    """
    Get metadata for all job types.

    Returns comprehensive metadata including labels, descriptions, colors,
    and other UI configuration for all registered job types.
    This endpoint provides a single source of truth for job type configuration.
    """
    return to_api_response()


def map_job_type_to_schema(model_type: str) -> str:
    """Map model JobType values to schema JobType values using the job registry."""
    mapping = get_job_type_mapping()
    return mapping.get(model_type, model_type)


@router.get("/active", response_model=JobsListResponse)
async def get_active_jobs_endpoint(
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> JobsListResponse:
    """
    Get currently active jobs (running, pending, cancelling).

    This endpoint returns only jobs that are currently active and need user attention.
    These jobs are updated in real-time and should be displayed prominently.
    """
    # Get active jobs from queue
    active_jobs = await job_service.get_active_jobs(db)

    # Filter by job_type if provided
    if job_type:
        active_jobs = [
            job
            for job in active_jobs
            if str(job.type.value if hasattr(job.type, "value") else job.type)
            == job_type
        ]

    # Sort by created_at descending (newest first)
    active_jobs.sort(key=lambda j: j.created_at, reverse=True)  # type: ignore[arg-type,return-value]

    # Convert to response models
    job_responses = []
    for job in active_jobs:
        # Ensure metadata is a dict
        job_metadata_dict: Dict[str, Any] = (
            job.job_metadata if isinstance(job.job_metadata, dict) else {}
        )

        job_responses.append(
            JobResponse(
                id=str(job.id),
                type=SchemaJobType(
                    map_job_type_to_schema(
                        str(job.type.value if hasattr(job.type, "value") else job.type)
                    )
                ),
                status=JobStatus(
                    job.status.value if hasattr(job.status, "value") else job.status
                ),
                progress=float(job.progress or 0),
                parameters={},
                metadata=job_metadata_dict,
                result=job.result,  # type: ignore[arg-type]
                error=job.error,  # type: ignore[arg-type]
                created_at=job.created_at,  # type: ignore[arg-type]
                updated_at=job.updated_at,  # type: ignore[arg-type]
                started_at=job.started_at,  # type: ignore[arg-type]
                completed_at=job.completed_at,  # type: ignore[arg-type]
                total=job.total_items,
                processed_items=job.processed_items,
            )
        )

    return JobsListResponse(jobs=job_responses)


@router.get("", response_model=JobsListResponse)
async def list_jobs(
    status: Optional[List[str]] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(50, le=100, description="Maximum number of jobs to return"),
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobsListResponse:
    """
    List recent jobs.

    Returns active jobs from the queue and recent completed jobs from the database.
    """
    # If filtering by specific job ID, return only that job
    if job_id:
        job = await job_service.get_job(job_id, db)
        if job:
            # Ensure metadata is a dict
            metadata_dict: Dict[str, Any] = (
                job.job_metadata if isinstance(job.job_metadata, dict) else {}
            )

            job_response = JobResponse(
                id=str(job.id),
                type=SchemaJobType(
                    map_job_type_to_schema(
                        str(job.type.value if hasattr(job.type, "value") else job.type)
                    )
                ),
                status=JobStatus(
                    job.status.value if hasattr(job.status, "value") else job.status
                ),
                progress=float(job.progress or 0),
                parameters={},
                metadata=metadata_dict,
                result=job.result,  # type: ignore[arg-type]
                error=job.error,  # type: ignore[arg-type]
                created_at=job.created_at,  # type: ignore[arg-type]
                updated_at=job.updated_at,  # type: ignore[arg-type]
                started_at=job.started_at,  # type: ignore[arg-type]
                completed_at=job.completed_at,  # type: ignore[arg-type]
                total=job.total_items,
                processed_items=job.processed_items,
            )
            return JobsListResponse(jobs=[job_response])
        else:
            return JobsListResponse(jobs=[])

    # Get active jobs from queue
    active_jobs = await job_service.get_active_jobs(db)

    # Get IDs of active jobs to exclude from DB query
    active_job_ids = [str(job.id) for job in active_jobs]

    # Filter active jobs by status if status filter is provided
    if status:
        active_jobs = [job for job in active_jobs if job.status in status]

    # Build database query
    if status:
        # Query DB for the requested statuses, but exclude jobs we already have from active_jobs
        query = select(Job).where(Job.status.in_(status))
        if active_job_ids:
            query = query.where(~Job.id.in_(active_job_ids))
    else:
        # Otherwise, exclude active jobs to avoid duplicates with queue
        query = select(Job).where(~Job.status.in_(["pending", "running"]))

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
        job_metadata_dict: Dict[str, Any] = (
            job.job_metadata if isinstance(job.job_metadata, dict) else {}
        )

        job_responses.append(
            JobResponse(
                id=str(job.id),
                type=SchemaJobType(
                    map_job_type_to_schema(
                        str(job.type.value if hasattr(job.type, "value") else job.type)
                    )
                ),
                status=JobStatus(
                    job.status.value if hasattr(job.status, "value") else job.status
                ),
                progress=float(job.progress or 0),
                parameters={},  # Empty dict for parameters since model doesn't have this field
                metadata=job_metadata_dict,  # Use job_metadata for metadata field
                result=job.result,  # type: ignore[arg-type]
                error=job.error,  # type: ignore[arg-type]
                created_at=job.created_at,  # type: ignore[arg-type]
                updated_at=job.updated_at,  # type: ignore[arg-type]
                started_at=job.started_at,  # type: ignore[arg-type]
                completed_at=job.completed_at,  # type: ignore[arg-type]
                total=job.total_items,  # Include progress tracking fields
                processed_items=job.processed_items,
            )
        )

    return JobsListResponse(jobs=job_responses)


@router.get("/recent-processed-torrents")
async def get_recent_processed_torrents(
    limit: int = Query(10, le=50, description="Maximum number of torrents to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get recently processed torrents with file counts.

    Returns a summary of the most recently processed torrents, showing:
    - Torrent name
    - Number of files processed
    - When they were processed
    """
    # Query to get torrents grouped by download_name with counts
    query = (
        select(
            HandledDownload.download_name,
            func.count(HandledDownload.id).label("file_count"),
            func.max(HandledDownload.timestamp).label("latest_timestamp"),
        )
        .group_by(HandledDownload.download_name)
        .order_by(func.max(HandledDownload.timestamp).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    torrents = result.all()

    return {
        "total": len(torrents),
        "torrents": [
            {
                "name": torrent.download_name,
                "file_count": torrent.file_count,
                "processed_at": torrent.latest_timestamp,
            }
            for torrent in torrents
        ],
    }


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
                str(job.type.value if hasattr(job.type, "value") else job.type)
            )
        ),
        status=JobStatus(
            job.status.value if hasattr(job.status, "value") else job.status
        ),
        progress=float(job.progress or 0),
        parameters={},  # Empty dict for parameters since model doesn't have this field
        metadata=metadata_dict,  # Use job_metadata for metadata field
        result=job.result,  # type: ignore[arg-type]
        error=job.error,  # type: ignore[arg-type]
        created_at=job.created_at,  # type: ignore[arg-type]
        updated_at=job.updated_at,  # type: ignore[arg-type]
        started_at=job.started_at,  # type: ignore[arg-type]
        completed_at=job.completed_at,  # type: ignore[arg-type]
        total=job.total_items,  # Include progress tracking fields
        processed_items=job.processed_items,
        logs=logs,
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cancel a running or pending job.

    This endpoint supports cancelling jobs in the following states:
    - PENDING: Job is queued but not started - will be immediately cancelled
    - RUNNING: Job is actively processing - will be marked for cancellation
    - CANCELLING: Cancellation already in progress

    Jobs in COMPLETED, FAILED, or CANCELLED states cannot be cancelled.

    Example responses:
    - Pending job: {"success": true, "message": "Job {job_id} cancelled successfully"}
    - Running job: {"success": true, "message": "Job {job_id} cancellation initiated"}
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


@router.websocket("/ws")
async def jobs_updates_ws(  # type: ignore[no-untyped-def]
    websocket: WebSocket,
    manager: WebSocketManager = Depends(get_websocket_manager),
):
    """
    WebSocket for real-time updates of all jobs.
    """
    await manager.connect(websocket)
    logger.info("Client connected to jobs WebSocket")

    try:
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (ping/pong)
                data = await websocket.receive_json()

                # Handle ping/pong
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                logger.info("Client disconnected from jobs WebSocket")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await manager.disconnect(websocket)


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
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
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
    # Convert string type back to JobType enum
    from app.models.job import JobType as ModelJobType

    job_type_enum = ModelJobType(job.type)

    new_job = await job_service.create_job(
        job_type=job_type_enum,
        metadata=metadata_dict,
        db=db,
    )

    # Refresh the job object to ensure all attributes are loaded
    await db.refresh(new_job)

    return {
        "success": True,
        "message": f"Job {job_id} retried as new job {new_job.id}",
        "new_job_id": new_job.id,
    }


@router.post("/cleanup")
async def trigger_cleanup(
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger a cleanup job manually.

    This will:
    - Find and update stale jobs (stuck in RUNNING/PENDING state)
    - Delete old completed jobs (older than 30 days)
    - Reset stuck PENDING plans to DRAFT status
    """
    # Check if there's already a cleanup job running
    query = select(Job).where(
        Job.type == "cleanup", Job.status.in_(["pending", "running"])
    )
    result = await db.execute(query)
    existing_job = result.scalar_one_or_none()

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cleanup job already {existing_job.status}: {existing_job.id}",
        )

    # Import JobType from models to use the enum
    from app.models.job import JobType as ModelJobType

    # Create a new cleanup job
    new_job = await job_service.create_job(
        job_type=ModelJobType.CLEANUP,
        metadata={"triggered_by": "manual", "source": "api"},
        db=db,
    )

    # Refresh the job object to ensure all attributes are loaded
    await db.refresh(new_job)

    return {
        "success": True,
        "message": "Cleanup job started successfully",
        "job_id": str(new_job.id),
    }


@router.post("/stash-scan")
async def trigger_stash_scan(
    paths: Optional[List[str]] = Body(
        None, description="Paths to scan (default: ['/data'])"
    ),
    rescan: bool = Body(
        False,
        description="Forces a rescan on files even if modification time is unchanged",
    ),
    scan_generate_covers: bool = Body(True, description="Generate covers during scan"),
    scan_generate_previews: bool = Body(
        True, description="Generate previews during scan"
    ),
    scan_generate_image_previews: bool = Body(
        False, description="Generate image previews during scan"
    ),
    scan_generate_sprites: bool = Body(
        True, description="Generate sprites during scan"
    ),
    scan_generate_phashes: bool = Body(
        True, description="Generate phashes during scan"
    ),
    scan_generate_thumbnails: bool = Body(
        False, description="Generate image thumbnails during scan"
    ),
    scan_generate_clip_previews: bool = Body(
        False, description="Generate image clip previews during scan"
    ),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger a Stash metadata scan job.

    This will start a metadata scan in Stash with the specified settings.
    The job will poll the Stash job status and report progress in real-time.
    """
    # Check if there's already a stash scan job running
    query = select(Job).where(
        Job.type == "stash_scan", Job.status.in_(["pending", "running"])
    )
    result = await db.execute(query)
    existing_job = result.scalar_one_or_none()

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stash scan job already {existing_job.status}: {existing_job.id}",
        )

    # Import JobType from models to use the enum
    from app.models.job import JobType as ModelJobType

    # Prepare metadata with scan settings
    job_metadata = {
        "triggered_by": "manual",
        "source": "api",
        "rescan": rescan,
        "scanGenerateCovers": scan_generate_covers,
        "scanGeneratePreviews": scan_generate_previews,
        "scanGenerateImagePreviews": scan_generate_image_previews,
        "scanGenerateSprites": scan_generate_sprites,
        "scanGeneratePhashes": scan_generate_phashes,
        "scanGenerateThumbnails": scan_generate_thumbnails,
        "scanGenerateClipPreviews": scan_generate_clip_previews,
    }

    if paths:
        job_metadata["paths"] = paths

    # Create a new stash scan job
    new_job = await job_service.create_job(
        job_type=ModelJobType.STASH_SCAN,
        metadata=job_metadata,
        db=db,
    )

    # Refresh the job object to ensure all attributes are loaded
    await db.refresh(new_job)

    return {
        "success": True,
        "message": "Stash scan job started successfully",
        "job_id": str(new_job.id),
        "stash_scan_settings": job_metadata,
    }


@router.post("/run")
async def run_job(
    job_type: str = Body(..., description="Type of job to run"),
    metadata: Optional[Dict[str, Any]] = Body(
        None, description="Job parameters and metadata"
    ),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run a job immediately with the specified type and parameters.

    This endpoint allows manual triggering of any registered job type.
    """
    # Import JobType from models to use the enum
    from app.models.job import JobType as ModelJobType

    # Validate job type
    try:
        model_job_type = ModelJobType(job_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job type: {job_type}. Valid types are: {[jt.value for jt in ModelJobType]}",
        )

    # Check if there's already a job of this type running
    query = select(Job).where(
        Job.type == job_type, Job.status.in_(["pending", "running"])
    )
    result = await db.execute(query)
    existing_job = result.scalar_one_or_none()

    if existing_job and job_type not in [
        "sync_scenes",
        "analysis",
        "apply_plan",
        "generate_details",
    ]:
        # Some job types can have multiple instances running
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{job_type} job already {existing_job.status}: {existing_job.id}",
        )

    # Merge metadata with defaults
    job_metadata = metadata or {}
    job_metadata.update(
        {
            "triggered_by": "manual",
            "source": "api",
        }
    )

    # Create the job
    new_job = await job_service.create_job(
        job_type=model_job_type,
        metadata=job_metadata,
        db=db,
    )

    # Refresh the job object to ensure all attributes are loaded
    await db.refresh(new_job)

    return {
        "success": True,
        "message": f"{job_type} job started successfully",
        "job_id": str(new_job.id),
        "job_type": job_type,
        "metadata": job_metadata,
    }


@router.get("/{job_id}/handled-downloads")
async def get_job_handled_downloads(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the list of downloads that were handled/processed by a job.

    This is specifically for process_downloads jobs to see which files were processed.
    """
    # First verify the job exists
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    # Get handled downloads for this job
    query = (
        select(HandledDownload)
        .where(HandledDownload.job_id == job_id)
        .order_by(HandledDownload.timestamp.desc())
    )
    result = await db.execute(query)
    downloads = result.scalars().all()

    return {
        "job_id": job_id,
        "total_downloads": len(downloads),
        "downloads": [
            {
                "id": download.id,
                "timestamp": download.timestamp,
                "download_name": download.download_name,
                "destination_path": download.destination_path,
            }
            for download in downloads
        ],
    }
