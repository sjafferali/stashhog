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

    # Eagerly load all attributes while still in session context
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

    # Eagerly load all attributes while still in session context
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

    # Eagerly load all attributes while still in session context
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

    # Eagerly load all attributes while still in session context
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

    # Eagerly load all attributes while still in session context
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


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(db: AsyncDBSession = Depends(get_db)) -> SyncStatsResponse:
    """
    Get sync statistics.

    Returns counts and last sync times for each entity type.

    Args:
        db: Database session

    Returns:
        Sync statistics
    """
    # Get last sync times for each entity type
    from sqlalchemy import func, select

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

    # Get pending sync counts (simplified)
    # In a real implementation, this would check which items need syncing
    pending_scenes = 0
    pending_performers = 0
    pending_tags = 0
    pending_studios = 0

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
        pending_performers=pending_performers,
        pending_tags=pending_tags,
        pending_studios=pending_studios,
    )
