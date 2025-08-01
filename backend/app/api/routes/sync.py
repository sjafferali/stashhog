"""
Sync management endpoints.
"""

from typing import List

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.api.schemas import JobResponse
from app.api.schemas import JobStatus as APIJobStatus
from app.api.schemas import JobType as APIJobType
from app.api.schemas import SyncResultResponse
from app.core.dependencies import (
    get_db,
    get_job_service,
    get_stash_service,
    get_sync_service,
)
from app.models import SyncHistory
from app.models.job import Job, JobStatus
from app.models.job import JobType as ModelJobType
from app.services.dashboard_status_service import DashboardStatusService
from app.services.job_service import JobService
from app.services.stash_service import StashService
from app.services.sync.sync_service import SyncService

router = APIRouter()


def _map_job_type(model_job_type: str) -> str:
    """Map model JobType values to API JobType values."""
    job_type_mapping = {
        "sync": "sync_all",
        "sync_scenes": "scene_sync",
        "sync_performers": "sync_all",
        "sync_tags": "sync_all",
        "sync_studios": "sync_all",
        "sync_all": "sync_all",
    }
    return job_type_mapping.get(model_job_type, "sync_all")


@router.post("/all", response_model=JobResponse)
async def sync_all(
    force: bool = Query(False, description="Force full sync ignoring timestamps"),
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Trigger full sync of all entities from Stash.

    This creates a background job to sync performers, tags, studios, and scenes.

    Args:
        force: Force full sync ignoring timestamps
        db: Database session

    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.SYNC, db=db, metadata={"force": force}
    )

    # Refresh the job object in the current session to ensure all attributes are loaded
    await db.refresh(job)

    # Now safely access all attributes
    job_id = str(job.id)
    job_created_at = job.created_at
    job_updated_at = job.updated_at

    return JobResponse(
        id=job_id,
        type=APIJobType.SYNC,
        status=APIJobStatus.PENDING,
        progress=0,
        parameters={"force": force},
        created_at=job_created_at,  # type: ignore[arg-type]
        updated_at=job_updated_at,  # type: ignore[arg-type]
        started_at=None,
        completed_at=None,
        result=None,
        error=None,
    )


@router.post("/scenes", response_model=JobResponse)
async def sync_scenes(
    body: dict = Body(...),
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Sync specific scenes from Stash.
    Note: This always performs a full sync of the specified scenes.

    Args:
        body: Request body containing scene_ids
        db: Database session

    Returns:
        Job information
    """
    scene_ids = body.get("scene_ids", [])

    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.SYNC_SCENES,
        db=db,
        metadata={"scene_ids": scene_ids},
    )

    # Refresh the job object in the current session to ensure all attributes are loaded
    await db.refresh(job)

    # Now safely access all attributes
    job_id = str(job.id)
    job_created_at = job.created_at
    job_updated_at = job.updated_at

    return JobResponse(
        id=job_id,
        type=APIJobType.SCENE_SYNC,
        status=APIJobStatus.PENDING,
        progress=0,
        parameters={"scene_ids": scene_ids},
        created_at=job_created_at,  # type: ignore[arg-type]
        updated_at=job_updated_at,  # type: ignore[arg-type]
        started_at=None,
        completed_at=None,
        result=None,
        error=None,
    )


@router.post("/scene/{scene_id}", response_model=SyncResultResponse)
async def sync_single_scene(
    scene_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncResultResponse:
    """
    Sync a single scene by ID.

    This is a synchronous operation that immediately syncs the scene.

    Args:
        scene_id: Scene ID to sync
        sync_service: Sync service instance

    Returns:
        Sync result
    """
    result = await sync_service.sync_scene_by_id(scene_id)

    return SyncResultResponse(
        job_id=result.job_id,
        status=result.status,
        total_items=result.total_items,
        processed_items=result.processed_items,
        created_items=result.created_items,
        updated_items=result.updated_items,
        skipped_items=result.skipped_items,
        failed_items=result.failed_items,
        started_at=result.started_at.isoformat() if result.started_at else None,
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        duration_seconds=result.duration_seconds,
        errors=[
            {"entity": e.entity_type, "id": e.entity_id, "message": e.message}
            for e in result.errors
        ],
    )


@router.get("/history")
async def get_sync_history(
    limit: int = Query(10, description="Number of items to return"),
    offset: int = Query(0, description="Number of items to skip"),
    db: AsyncDBSession = Depends(get_db),
) -> List[dict]:
    """
    Get sync history.

    Returns recent sync operations with their details.

    Args:
        limit: Number of items to return
        offset: Number of items to skip
        db: Database session

    Returns:
        List of sync history entries
    """
    from sqlalchemy import select

    query = (
        select(SyncHistory)
        .order_by(SyncHistory.started_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    history_items = result.scalars().all()

    return [
        {
            "id": str(item.id),
            "entity_type": item.entity_type,
            "status": item.status,
            "started_at": item.started_at.isoformat() if item.started_at else None,
            "completed_at": (
                item.completed_at.isoformat() if item.completed_at else None
            ),
            "total_items": item.items_synced,
            "processed_items": item.items_synced,
            "created_items": item.items_created,
            "updated_items": item.items_updated,
            "skipped_items": 0,
            "failed_items": item.items_failed,
            "error": item.error_details,
        }
        for item in history_items
    ]


@router.post("/stop")
async def stop_sync(
    job_service: JobService = Depends(get_job_service),
    db: AsyncDBSession = Depends(get_db),
) -> dict:
    """
    Stop any running sync operations.

    Returns:
        Status message
    """
    # Get all running sync jobs
    query = select(Job).where(
        Job.type.in_(
            [
                ModelJobType.SYNC,
                ModelJobType.SYNC_SCENES,
            ]
        ),
        Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]),
    )

    result = await db.execute(query)
    jobs = result.scalars().all()

    cancelled_count = 0
    for job in jobs:
        await job_service.cancel_job(str(job.id), db)
        cancelled_count += 1

    return {"message": f"Cancelled {cancelled_count} sync job(s)"}


@router.get("/stats", response_model=dict)
async def get_sync_stats(
    db: AsyncDBSession = Depends(get_db),
    stash_service: StashService = Depends(get_stash_service),
) -> dict:
    """
    Get comprehensive dashboard metrics including actionable items.

    Returns metrics for:
    - Pending sync items
    - Analysis status
    - Plan status
    - Scene organization status
    - Download processing status
    """
    # Use the centralized dashboard status service
    dashboard_service = DashboardStatusService(stash_service)
    return await dashboard_service.get_all_status_data(db)


@router.post("/downloads", response_model=JobResponse)
async def process_downloads(
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Process completed downloads from qBittorrent.

    This creates a background job to:
    1. Check for completed torrents with category "xxx"
    2. Copy files to /downloads/avideos/
    3. Add "synced" tag to processed torrents

    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.PROCESS_DOWNLOADS, db=db, metadata={}
    )

    # Refresh the job object in the current session to ensure all attributes are loaded
    await db.refresh(job)

    # Now safely access all attributes
    job_id = str(job.id)
    job_created_at = job.created_at
    job_updated_at = job.updated_at

    return JobResponse(
        id=job_id,
        type=APIJobType.PROCESS_DOWNLOADS,
        status=APIJobStatus.PENDING,
        progress=0,
        parameters={},
        created_at=job_created_at,  # type: ignore[arg-type]
        updated_at=job_updated_at,  # type: ignore[arg-type]
        started_at=None,
        completed_at=None,
        result=None,
        error=None,
    )
