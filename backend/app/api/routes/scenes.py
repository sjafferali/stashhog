"""
Scene management endpoints.
"""
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    SceneResponse,
    SceneFilter,
    PaginatedResponse,
    SuccessResponse,
    JobResponse,
    JobType,
    JobStatus,
    PaginationParams,
    PerformerResponse,
    TagResponse,
    StudioResponse
)
from app.core.dependencies import get_db, get_sync_service, get_job_queue
from app.core.exceptions import SceneNotFoundError
from app.models import Scene, Performer, Tag, Studio
from app.services.sync_service import SyncService
from app.services.job_queue import JobQueue

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[SceneResponse])
async def list_scenes(
    pagination: PaginationParams = Depends(),
    filters: SceneFilter = Depends(),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[SceneResponse]:
    """
    List scenes with pagination and filters.
    """
    # Build base query
    query = select(Scene).options(
        selectinload(Scene.performers),
        selectinload(Scene.tags),
        selectinload(Scene.studio)
    )
    
    # Apply filters
    conditions = []
    
    if filters.search:
        search_term = f"%{filters.search}%"
        conditions.append(
            or_(
                Scene.title.ilike(search_term),
                Scene.details.ilike(search_term)
            )
        )
    
    if filters.studio_id:
        conditions.append(Scene.studio_id == filters.studio_id)
    
    if filters.performer_ids:
        query = query.join(Scene.performers)
        conditions.append(Performer.id.in_(filters.performer_ids))
    
    if filters.tag_ids:
        query = query.join(Scene.tags)
        conditions.append(Tag.id.in_(filters.tag_ids))
    
    if filters.organized is not None:
        conditions.append(Scene.organized == filters.organized)
    
    if filters.date_from:
        conditions.append(Scene.scene_date >= filters.date_from)
    
    if filters.date_to:
        conditions.append(Scene.scene_date <= filters.date_to)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply sorting
    if pagination.sort_by:
        sort_column = getattr(Scene, pagination.sort_by, None)
        if sort_column:
            if pagination.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column)
    else:
        query = query.order_by(Scene.created_date.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Apply pagination
    query = query.offset((pagination.page - 1) * pagination.per_page).limit(pagination.per_page)
    
    # Execute query
    result = await db.execute(query)
    scenes = result.scalars().unique().all()
    
    # Transform to response models
    scene_responses = []
    for scene in scenes:
        scene_responses.append(SceneResponse(
            id=scene.id,
            title=scene.title,
            paths=scene.paths,
            organized=scene.organized,
            details=scene.details,
            created_date=scene.created_date,
            scene_date=scene.scene_date,
            studio=StudioResponse(
                id=scene.studio.id,
                name=scene.studio.name
            ) if scene.studio else None,
            performers=[
                PerformerResponse(
                    id=p.id,
                    name=p.name
                ) for p in scene.performers
            ],
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name
                ) for t in scene.tags
            ],
            last_synced=scene.last_synced
        ))
    
    return PaginatedResponse.create(
        items=scene_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page
    )


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: str,
    db: AsyncSession = Depends(get_db)
) -> SceneResponse:
    """
    Get a single scene by ID.
    """
    # Query scene with relationships
    query = select(Scene).options(
        selectinload(Scene.performers),
        selectinload(Scene.tags),
        selectinload(Scene.studio)
    ).where(Scene.id == scene_id)
    
    result = await db.execute(query)
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene {scene_id} not found"
        )
    
    # Transform to response model
    return SceneResponse(
        id=scene.id,
        title=scene.title,
        paths=scene.paths,
        organized=scene.organized,
        details=scene.details,
        created_date=scene.created_date,
        scene_date=scene.scene_date,
        studio=StudioResponse(
            id=scene.studio.id,
            name=scene.studio.name
        ) if scene.studio else None,
        performers=[
            PerformerResponse(
                id=p.id,
                name=p.name
            ) for p in scene.performers
        ],
        tags=[
            TagResponse(
                id=t.id,
                name=t.name
            ) for t in scene.tags
        ],
        last_synced=scene.last_synced
    )


@router.post("/sync")
async def sync_scenes(
    background: bool = Query(True, description="Run as background job"),
    incremental: bool = Query(True, description="Only sync new/updated scenes"),
    job_queue: JobQueue = Depends(get_job_queue),
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger scene synchronization from Stash.
    """
    if background:
        # Queue as background job
        job_id = await job_queue.enqueue(
            job_type=JobType.SCENE_SYNC,
            params={
                "incremental": incremental
            }
        )
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Scene sync job has been queued"
        }
    else:
        # Run synchronously
        result = await sync_service.sync_scenes(incremental=incremental)
        return {
            "status": "completed",
            "scenes_processed": result.get("processed", 0),
            "scenes_created": result.get("created", 0),
            "scenes_updated": result.get("updated", 0),
            "errors": result.get("errors", [])
        }


@router.post("/{scene_id}/resync", response_model=SceneResponse)
async def resync_scene(
    scene_id: str,
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db)
) -> SceneResponse:
    """
    Resync a single scene from Stash.
    """
    # Verify scene exists
    query = select(Scene).where(Scene.id == scene_id)
    result = await db.execute(query)
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene {scene_id} not found"
        )
    
    # Sync single scene
    await sync_service.sync_single_scene(scene.stash_id)
    
    # Get updated scene
    await db.refresh(scene)
    
    # Return updated scene
    return await get_scene(scene_id, db)


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_scene_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get scene statistics summary.
    """
    # Get total scenes
    total_query = select(func.count(Scene.id))
    total_result = await db.execute(total_query)
    total_scenes = total_result.scalar_one()
    
    # Get organized scenes
    organized_query = select(func.count(Scene.id)).where(Scene.organized == True)
    organized_result = await db.execute(organized_query)
    organized_scenes = organized_result.scalar_one()
    
    # Get entity counts
    tag_count_query = select(func.count(Tag.id))
    tag_result = await db.execute(tag_count_query)
    total_tags = tag_result.scalar_one()
    
    performer_count_query = select(func.count(Performer.id))
    performer_result = await db.execute(performer_count_query)
    total_performers = performer_result.scalar_one()
    
    studio_count_query = select(func.count(Studio.id))
    studio_result = await db.execute(studio_count_query)
    total_studios = studio_result.scalar_one()
    
    # Get scenes by studio
    studio_stats_query = (
        select(Studio.name, func.count(Scene.id).label("count"))
        .join(Scene, Scene.studio_id == Studio.id)
        .group_by(Studio.name)
        .order_by(func.count(Scene.id).desc())
        .limit(10)
    )
    studio_stats_result = await db.execute(studio_stats_query)
    scenes_by_studio = {row[0]: row[1] for row in studio_stats_result}
    
    return {
        "total_scenes": total_scenes,
        "organized_scenes": organized_scenes,
        "organization_percentage": (organized_scenes / total_scenes * 100) if total_scenes > 0 else 0,
        "total_tags": total_tags,
        "total_performers": total_performers,
        "total_studios": total_studios,
        "scenes_by_studio": scenes_by_studio
    }