"""
Sync management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.api.schemas import JobResponse
from app.api.schemas import JobStatus as APIJobStatus
from app.api.schemas import JobType as APIJobType
from app.api.schemas import SyncResultResponse, SyncStatsResponse
from app.core.dependencies import (
    get_db,
    get_job_service,
    get_sync_service,
)
from app.models import SyncHistory
from app.models.job import JobType as ModelJobType
from app.services.job_service import JobService
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
        type=APIJobType.SYNC_ALL,
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
    scene_ids: Optional[List[str]] = None,
    force: bool = Query(False, description="Force sync even if unchanged"),
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Sync scenes from Stash.

    Args:
        scene_ids: Specific scene IDs to sync (if not provided, syncs all)
        force: Force sync even if scenes are unchanged
        db: Database session

    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.SYNC_SCENES,
        db=db,
        metadata={"scene_ids": scene_ids, "force": force},
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
        parameters={"scene_ids": scene_ids, "force": force},
        created_at=job_created_at,  # type: ignore[arg-type]
        updated_at=job_updated_at,  # type: ignore[arg-type]
        started_at=None,
        completed_at=None,
        result=None,
        error=None,
    )


@router.post("/performers", response_model=JobResponse)
async def sync_performers(
    force: bool = Query(False, description="Force sync ignoring timestamps"),
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Sync performers from Stash.

    Args:
        force: Force sync ignoring timestamps
        db: Database session

    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.SYNC_PERFORMERS, db=db, metadata={"force": force}
    )

    # Refresh the job object in the current session to ensure all attributes are loaded
    await db.refresh(job)

    # Now safely access all attributes
    job_id = str(job.id)
    job_created_at = job.created_at
    job_updated_at = job.updated_at

    return JobResponse(
        id=job_id,
        type=APIJobType.SYNC_PERFORMERS,
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


@router.post("/tags", response_model=JobResponse)
async def sync_tags(
    force: bool = Query(False, description="Force sync ignoring timestamps"),
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Sync tags from Stash.

    Args:
        force: Force sync ignoring timestamps
        db: Database session

    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.SYNC_TAGS, db=db, metadata={"force": force}
    )

    # Refresh the job object in the current session to ensure all attributes are loaded
    await db.refresh(job)

    # Now safely access all attributes
    job_id = str(job.id)
    job_created_at = job.created_at
    job_updated_at = job.updated_at

    return JobResponse(
        id=job_id,
        type=APIJobType.SYNC_TAGS,
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


@router.post("/studios", response_model=JobResponse)
async def sync_studios(
    force: bool = Query(False, description="Force sync ignoring timestamps"),
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Sync studios from Stash.

    Args:
        force: Force sync ignoring timestamps
        db: Database session

    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=ModelJobType.SYNC_STUDIOS, db=db, metadata={"force": force}
    )

    # Refresh the job object in the current session to ensure all attributes are loaded
    await db.refresh(job)

    # Now safely access all attributes
    job_id = str(job.id)
    job_created_at = job.created_at
    job_updated_at = job.updated_at

    return JobResponse(
        id=job_id,
        type=APIJobType.SYNC_STUDIOS,
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
            "total_items": item.total_items,
            "processed_items": item.processed_items,
            "created_items": item.created_items,
            "updated_items": item.updated_items,
            "skipped_items": item.skipped_items,
            "failed_items": item.failed_items,
            "error": item.error,
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
    from sqlalchemy import select

    from app.models.job import Job, JobStatus

    query = select(Job).where(
        Job.type.in_(
            [
                ModelJobType.SYNC,
                ModelJobType.SYNC_SCENES,
                ModelJobType.SYNC_PERFORMERS,
                ModelJobType.SYNC_TAGS,
                ModelJobType.SYNC_STUDIOS,
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


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    db: AsyncDBSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncStatsResponse:
    """
    Get sync statistics.

    Returns counts and last sync times for each entity type.

    Args:
        db: Database session
        sync_service: Sync service instance

    Returns:
        Sync statistics
    """
    # Get last sync times for each entity type
    from sqlalchemy import func, select

    from app.models.job import Job, JobStatus

    last_syncs = {}
    for entity_type in ["scene", "performer", "tag", "studio"]:
        query = (
            select(SyncHistory)
            .where(
                SyncHistory.entity_type == entity_type,
                SyncHistory.status == "completed",
            )
            .order_by(SyncHistory.completed_at.desc())
            .limit(1)
        )

        result = await db.execute(query)
        last_sync = result.scalar_one_or_none()

        if last_sync:
            last_syncs[entity_type] = last_sync.completed_at.isoformat()

    # Get counts from database
    from app.models import Performer, Scene, Studio, Tag

    scene_count_result = await db.execute(select(func.count(Scene.id)))
    scene_count = scene_count_result.scalar_one()

    performer_count_result = await db.execute(select(func.count(Performer.id)))
    performer_count = performer_count_result.scalar_one()

    tag_count_result = await db.execute(select(func.count(Tag.id)))
    tag_count = tag_count_result.scalar_one()

    studio_count_result = await db.execute(select(func.count(Studio.id)))
    studio_count = studio_count_result.scalar_one()

    # Calculate pending sync counts
    # Check for scenes that have been updated in Stash since last sync
    pending_scenes = 0
    if last_syncs.get("scene"):
        try:
            # Get scenes from Stash that were updated after last sync
            from datetime import datetime

            last_sync_time = datetime.fromisoformat(
                last_syncs["scene"].replace("Z", "+00:00")
            )

            # This would need to query Stash API to get updated scenes count
            # For now, we'll check local scenes that might need re-sync
            pending_query = select(func.count(Scene.id)).where(
                Scene.updated_at > last_sync_time
            )
            result = await db.execute(pending_query)
            pending_scenes = result.scalar_one() or 0
        except Exception:
            pending_scenes = 0

    # Check if there's an active sync job
    is_syncing = False
    sync_job_query = select(Job).where(
        Job.type.in_(
            [
                ModelJobType.SYNC,
                ModelJobType.SYNC_SCENES,
                ModelJobType.SYNC_PERFORMERS,
                ModelJobType.SYNC_TAGS,
                ModelJobType.SYNC_STUDIOS,
            ]
        ),
        Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]),
    )
    result = await db.execute(sync_job_query)
    active_jobs = result.scalars().all()
    is_syncing = len(active_jobs) > 0

    return SyncStatsResponse(
        scene_count=scene_count,
        performer_count=performer_count,
        tag_count=tag_count,
        studio_count=studio_count,
        last_scene_sync=last_syncs.get("scene"),
        last_performer_sync=last_syncs.get("performer"),
        last_tag_sync=last_syncs.get("tag"),
        last_studio_sync=last_syncs.get("studio"),
        pending_scenes=pending_scenes,
        pending_performers=0,  # Simplified for now
        pending_tags=0,  # Simplified for now
        pending_studios=0,  # Simplified for now
        is_syncing=is_syncing,
    )
