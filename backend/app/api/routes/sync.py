"""
Sync management endpoints.
"""

from datetime import timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
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
    """
    # Get basic counts
    from app.models import AnalysisPlan, Performer, Scene, Studio, Tag
    from app.models.analysis_plan import PlanStatus

    scene_count_result = await db.execute(select(func.count(Scene.id)))
    scene_count = scene_count_result.scalar_one()

    performer_count_result = await db.execute(select(func.count(Performer.id)))
    performer_count = performer_count_result.scalar_one()

    tag_count_result = await db.execute(select(func.count(Tag.id)))
    tag_count = tag_count_result.scalar_one()

    studio_count_result = await db.execute(select(func.count(Studio.id)))
    studio_count = studio_count_result.scalar_one()

    # Get sync status
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

    # Get pending scenes count
    pending_scenes = 0
    if last_syncs.get("scene"):
        try:
            from datetime import datetime

            last_sync_time = datetime.fromisoformat(
                last_syncs["scene"].replace("Z", "+00:00")
            )
            filter_dict = {
                "updated_at": {
                    "value": last_sync_time.isoformat(),
                    "modifier": "GREATER_THAN",
                }
            }
            _, total_count = await stash_service.get_scenes(
                page=1, per_page=1, filter=filter_dict
            )
            pending_scenes = total_count
        except Exception:
            pending_scenes = 0

    # Check if sync is running
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

    # Get analysis metrics
    # Scenes not analyzed
    not_analyzed_query = select(func.count(Scene.id)).where(Scene.analyzed.is_(False))
    not_analyzed_result = await db.execute(not_analyzed_query)
    scenes_not_analyzed = not_analyzed_result.scalar_one()

    # Scenes not video analyzed
    not_video_analyzed_query = select(func.count(Scene.id)).where(
        Scene.video_analyzed.is_(False)
    )
    not_video_analyzed_result = await db.execute(not_video_analyzed_query)
    scenes_not_video_analyzed = not_video_analyzed_result.scalar_one()

    # Unorganized scenes
    unorganized_query = select(func.count(Scene.id)).where(Scene.organized.is_(False))
    unorganized_result = await db.execute(unorganized_query)
    unorganized_scenes = unorganized_result.scalar_one()

    # Analysis plans by status
    draft_plans_query = select(func.count(AnalysisPlan.id)).where(
        AnalysisPlan.status == PlanStatus.DRAFT
    )
    draft_plans_result = await db.execute(draft_plans_query)
    draft_plans = draft_plans_result.scalar_one()

    reviewing_plans_query = select(func.count(AnalysisPlan.id)).where(
        AnalysisPlan.status == PlanStatus.REVIEWING
    )
    reviewing_plans_result = await db.execute(reviewing_plans_query)
    reviewing_plans = reviewing_plans_result.scalar_one()

    # Check if analysis job is running
    is_analyzing = False
    analysis_job_query = select(Job).where(
        Job.type == ModelJobType.ANALYSIS,
        Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]),
    )
    result = await db.execute(analysis_job_query)
    analysis_jobs = result.scalars().all()
    is_analyzing = len(analysis_jobs) > 0

    # Get running jobs
    running_jobs_query = (
        select(Job)
        .where(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))
        .order_by(Job.created_at.desc())
        .limit(5)
    )
    running_result = await db.execute(running_jobs_query)
    running_jobs = running_result.scalars().all()

    # Get recently completed jobs
    completed_jobs_query = (
        select(Job)
        .where(
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
        )
        .order_by(Job.completed_at.desc().nullslast(), Job.updated_at.desc())
        .limit(10)
    )
    completed_result = await db.execute(completed_jobs_query)
    completed_jobs = completed_result.scalars().all()

    # Get additional metrics
    # Scenes without files
    scenes_without_files_query = select(func.count(Scene.id)).where(~Scene.files.any())
    scenes_without_files_result = await db.execute(scenes_without_files_query)
    scenes_without_files = scenes_without_files_result.scalar_one()

    # Failed jobs in last 24 hours
    from datetime import datetime, timedelta

    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_jobs_query = select(func.count(Job.id)).where(
        Job.status == JobStatus.FAILED, Job.completed_at >= twenty_four_hours_ago
    )
    failed_jobs_result = await db.execute(failed_jobs_query)
    recent_failed_jobs = failed_jobs_result.scalar_one()

    # Scenes missing key metadata
    scenes_missing_details_query = select(func.count(Scene.id)).where(
        or_(Scene.details.is_(None), Scene.details == "")
    )
    scenes_missing_details_result = await db.execute(scenes_missing_details_query)
    scenes_missing_details = scenes_missing_details_result.scalar_one()

    # Scenes without studio
    scenes_without_studio_query = select(func.count(Scene.id)).where(
        Scene.studio_id.is_(None)
    )
    scenes_without_studio_result = await db.execute(scenes_without_studio_query)
    scenes_without_studio = scenes_without_studio_result.scalar_one()

    # Scenes without performers
    scenes_without_performers_query = select(func.count(Scene.id)).where(
        ~Scene.performers.any()
    )
    scenes_without_performers_result = await db.execute(scenes_without_performers_query)
    scenes_without_performers = scenes_without_performers_result.scalar_one()

    # Scenes without tags
    scenes_without_tags_query = select(func.count(Scene.id)).where(~Scene.tags.any())
    scenes_without_tags_result = await db.execute(scenes_without_tags_query)
    scenes_without_tags = scenes_without_tags_result.scalar_one()

    return {
        "summary": {
            "scene_count": scene_count,
            "performer_count": performer_count,
            "tag_count": tag_count,
            "studio_count": studio_count,
        },
        "sync": {
            "last_scene_sync": last_syncs.get("scene"),
            "last_performer_sync": last_syncs.get("performer"),
            "last_tag_sync": last_syncs.get("tag"),
            "last_studio_sync": last_syncs.get("studio"),
            "pending_scenes": pending_scenes,
            "is_syncing": is_syncing,
        },
        "analysis": {
            "scenes_not_analyzed": scenes_not_analyzed,
            "scenes_not_video_analyzed": scenes_not_video_analyzed,
            "draft_plans": draft_plans,
            "reviewing_plans": reviewing_plans,
            "is_analyzing": is_analyzing,
        },
        "organization": {
            "unorganized_scenes": unorganized_scenes,
        },
        "metadata": {
            "scenes_without_files": scenes_without_files,
            "scenes_missing_details": scenes_missing_details,
            "scenes_without_studio": scenes_without_studio,
            "scenes_without_performers": scenes_without_performers,
            "scenes_without_tags": scenes_without_tags,
        },
        "jobs": {
            "recent_failed_jobs": recent_failed_jobs,
            "running_jobs": [
                {
                    "id": str(job.id),
                    "type": (
                        job.type.value if hasattr(job.type, "value") else str(job.type)
                    ),
                    "status": (
                        job.status.value
                        if hasattr(job.status, "value")
                        else str(job.status)
                    ),
                    "progress": job.progress,
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else None
                    ),
                    "metadata": (
                        job.job_metadata
                        if hasattr(job, "job_metadata")
                        and isinstance(job.job_metadata, dict)
                        else {}
                    ),
                }
                for job in running_jobs
            ],
            "completed_jobs": [
                {
                    "id": str(job.id),
                    "type": (
                        job.type.value if hasattr(job.type, "value") else str(job.type)
                    ),
                    "status": (
                        job.status.value
                        if hasattr(job.status, "value")
                        else str(job.status)
                    ),
                    "completed_at": (
                        job.completed_at.isoformat() if job.completed_at else None
                    ),
                    "error": job.error,
                    "result": job.result if isinstance(job.result, dict) else {},
                }
                for job in completed_jobs
            ],
        },
        "actionable_items": [
            {
                "id": "pending_sync",
                "type": "sync",
                "title": "Pending Sync",
                "description": f"{pending_scenes} scenes have been updated in Stash since last sync",
                "count": pending_scenes,
                "action": "sync_scenes",
                "action_label": "Run Incremental Sync",
                "priority": "high" if pending_scenes > 10 else "medium",
                "visible": pending_scenes > 0,
            },
            {
                "id": "draft_plans",
                "type": "analysis",
                "title": "Draft Plans",
                "description": f"{draft_plans} analysis plans are in draft status",
                "count": draft_plans,
                "action": "view_plans",
                "action_label": "Review Plans",
                "route": "/analysis/plans?status=draft",
                "priority": "medium",
                "visible": draft_plans > 0,
            },
            {
                "id": "reviewing_plans",
                "type": "analysis",
                "title": "Plans Under Review",
                "description": f"{reviewing_plans} analysis plans are being reviewed",
                "count": reviewing_plans,
                "action": "view_plans",
                "action_label": "Continue Review",
                "route": "/analysis/plans?status=reviewing",
                "priority": "high",
                "visible": reviewing_plans > 0,
            },
            {
                "id": "scenes_not_analyzed",
                "type": "analysis",
                "title": "Scenes Pending Analysis",
                "description": f"{scenes_not_analyzed} scenes have not been analyzed yet",
                "count": scenes_not_analyzed,
                "action": "view_scenes",
                "action_label": "View Scenes",
                "route": "/scenes?analyzed=false",
                "priority": "medium",
                "visible": scenes_not_analyzed > 0,
            },
            {
                "id": "scenes_not_video_analyzed",
                "type": "analysis",
                "title": "Scenes Pending Video Analysis",
                "description": f"{scenes_not_video_analyzed} scenes have not been video analyzed",
                "count": scenes_not_video_analyzed,
                "action": "view_scenes",
                "action_label": "View Scenes",
                "route": "/scenes?video_analyzed=false",
                "priority": "low",
                "visible": scenes_not_video_analyzed > 0,
            },
            {
                "id": "unorganized_scenes",
                "type": "organization",
                "title": "Unorganized Scenes",
                "description": f"{unorganized_scenes} scenes are not organized",
                "count": unorganized_scenes,
                "action": "view_scenes",
                "action_label": "View Unorganized",
                "route": "/scenes?organized=false",
                "priority": "low",
                "visible": unorganized_scenes > 0,
            },
            {
                "id": "scenes_without_files",
                "type": "sync",
                "title": "Scenes Without Files",
                "description": f"{scenes_without_files} scenes have no associated files",
                "count": scenes_without_files,
                "action": "view_scenes",
                "action_label": "View Broken Scenes",
                "route": "/scenes?has_files=false",
                "priority": "high" if scenes_without_files > 0 else "low",
                "visible": scenes_without_files > 0,
            },
            {
                "id": "recent_failed_jobs",
                "type": "system",
                "title": "Recent Failed Jobs",
                "description": f"{recent_failed_jobs} jobs failed in the last 24 hours",
                "count": recent_failed_jobs,
                "action": "view_jobs",
                "action_label": "View Failed Jobs",
                "route": "/jobs?status=failed",
                "priority": "high" if recent_failed_jobs > 5 else "medium",
                "visible": recent_failed_jobs > 0,
            },
            {
                "id": "scenes_missing_metadata",
                "type": "analysis",
                "title": "Scenes Missing Metadata",
                "description": f"{scenes_missing_details} scenes have no details",
                "count": scenes_missing_details,
                "action": "analyze_scenes",
                "action_label": "View Scenes",
                "batch_size": min(scenes_missing_details, 50),
                "priority": "low",
                "visible": scenes_missing_details > 10,
            },
        ],
    }


@router.post("/downloads", response_model=JobResponse)
async def process_downloads(
    db: AsyncDBSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Process completed downloads from qBittorrent.

    This creates a background job to:
    1. Check for completed torrents with category "xxx"
    2. Copy files to /opt/media/downloads/avideos/
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
