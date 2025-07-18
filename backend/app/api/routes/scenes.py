"""
Scene management endpoints.
"""

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    PaginatedResponse,
    PaginationParams,
    PerformerResponse,
    SceneFilter,
    SceneResponse,
    StudioResponse,
    TagResponse,
)
from app.core.dependencies import get_db, get_job_service, get_sync_service
from app.models import Performer, Scene, Studio, Tag
from app.models.job import JobType as ModelJobType
from app.services.job_service import JobService
from app.services.sync.sync_service import SyncService

router = APIRouter()


def _build_scene_filter_conditions(
    filters: SceneFilter, query: Any
) -> tuple[Any, list[Any]]:
    """Build filter conditions for scene query."""
    conditions = []

    if filters.search:
        search_term = f"%{filters.search}%"
        conditions.append(
            or_(
                Scene.title.ilike(search_term),
                Scene.details.ilike(search_term),
                # Search in paths JSON array - cast to string for simple LIKE search
                cast(Scene.paths, String).ilike(search_term),
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

    if filters.analyzed is not None:
        conditions.append(Scene.analyzed == filters.analyzed)

    if filters.video_analyzed is not None:
        conditions.append(Scene.video_analyzed == filters.video_analyzed)

    if filters.date_from:
        conditions.append(Scene.stash_date >= filters.date_from)

    if filters.date_to:
        conditions.append(Scene.stash_date <= filters.date_to)

    return query, conditions


def _apply_scene_sorting(query: Any, pagination: PaginationParams) -> Any:
    """Apply sorting to scene query."""
    if pagination.sort_by:
        sort_column = getattr(Scene, pagination.sort_by, None)
        if sort_column:
            if pagination.sort_order == "desc":
                return query.order_by(sort_column.desc())
            else:
                return query.order_by(sort_column)
    return query.order_by(Scene.stash_created_at.desc())


def _transform_scene_to_response(scene: Scene) -> SceneResponse:
    """Transform Scene model to SceneResponse."""
    # Use filename if title is empty or blank
    title = scene.title
    if not title or not title.strip():
        # First try to use actual file path if available
        if scene.file_path:
            title = os.path.basename(scene.file_path)
        # Fall back to paths array if no file_path
        elif scene.paths and len(scene.paths) > 0:
            title = os.path.basename(scene.paths[0])

    return SceneResponse(
        id=scene.id,  # type: ignore[arg-type]
        title=title,  # type: ignore[arg-type]
        paths=scene.paths,  # type: ignore[arg-type]
        file_path=scene.file_path,  # type: ignore[arg-type]
        organized=scene.organized,  # type: ignore[arg-type]
        analyzed=scene.analyzed,  # type: ignore[arg-type]
        details=scene.details,  # type: ignore[arg-type]
        stash_created_at=scene.stash_created_at,  # type: ignore[arg-type]
        stash_updated_at=scene.stash_updated_at,  # type: ignore[arg-type]
        stash_date=scene.stash_date,  # type: ignore[arg-type]
        studio=(
            StudioResponse(id=scene.studio.id, name=scene.studio.name, scene_count=0)
            if scene.studio
            else None
        ),
        performers=[
            PerformerResponse(id=p.id, name=p.name, scene_count=0)
            for p in scene.performers
        ],
        tags=[TagResponse(id=t.id, name=t.name, scene_count=0) for t in scene.tags],
        last_synced=scene.last_synced,  # type: ignore[arg-type]
        # Metadata fields
        duration=scene.duration,  # type: ignore[arg-type]
        size=scene.size,  # type: ignore[arg-type]
        width=scene.width,  # type: ignore[arg-type]
        height=scene.height,  # type: ignore[arg-type]
        framerate=scene.framerate,  # type: ignore[arg-type]
        bitrate=scene.bitrate,  # type: ignore[arg-type]
        video_codec=scene.codec,  # type: ignore[arg-type]
    )


@router.get("", response_model=PaginatedResponse[SceneResponse])
async def list_scenes(
    pagination: PaginationParams = Depends(),
    filters: SceneFilter = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SceneResponse]:
    """
    List scenes with pagination and filters.
    """
    # Build base query
    query = select(Scene).options(
        selectinload(Scene.performers),
        selectinload(Scene.tags),
        selectinload(Scene.studio),
    )

    # Apply filters
    query, conditions = _build_scene_filter_conditions(filters, query)
    if conditions:
        query = query.where(and_(*conditions))

    # Apply sorting
    query = _apply_scene_sorting(query, pagination)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    query = query.offset((pagination.page - 1) * pagination.per_page).limit(
        pagination.per_page
    )

    # Execute query
    result = await db.execute(query)
    scenes = result.scalars().unique().all()

    # Transform to response models
    scene_responses = [_transform_scene_to_response(scene) for scene in scenes]  # type: ignore[arg-type]

    return PaginatedResponse.create(
        items=scene_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: str, db: AsyncSession = Depends(get_db)) -> SceneResponse:
    """
    Get a single scene by ID.
    """
    # Query scene with relationships
    query = (
        select(Scene)
        .options(
            selectinload(Scene.performers),
            selectinload(Scene.tags),
            selectinload(Scene.studio),
        )
        .where(Scene.id == scene_id)
    )

    result = await db.execute(query)
    scene = result.scalar_one_or_none()

    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found"
        )

    # Transform to response model
    return _transform_scene_to_response(scene)


@router.post("/sync")
async def sync_scenes(
    background: bool = Query(True, description="Run as background job"),
    incremental: bool = Query(True, description="Only sync new/updated scenes"),
    job_service: JobService = Depends(get_job_service),
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger scene synchronization from Stash.
    """
    if background:
        # Queue as background job
        job = await job_service.create_job(
            job_type=ModelJobType.SYNC_SCENES,
            db=db,
            metadata={"incremental": incremental},
        )
        # Refresh the job object to ensure all attributes are loaded
        await db.refresh(job)
        return {
            "job_id": job.id,
            "status": "queued",
            "message": "Scene sync job has been queued",
        }
    else:
        # Run synchronously
        result = await sync_service.sync_scenes()
        return {
            "status": "completed",
            "scenes_processed": (
                result.processed_items if hasattr(result, "processed_items") else 0
            ),
            "scenes_created": (
                result.created_items if hasattr(result, "created_items") else 0
            ),
            "scenes_updated": (
                result.updated_items if hasattr(result, "updated_items") else 0
            ),
            "errors": result.errors if hasattr(result, "errors") else [],
        }


@router.post("/{scene_id}/resync", response_model=SceneResponse)
async def resync_scene(
    scene_id: str,
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db),
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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found"
        )

    # Sync single scene
    await sync_service.sync_scene_by_id(scene.id)  # type: ignore[arg-type]

    # Get updated scene
    await db.refresh(scene)

    # Return updated scene
    return await get_scene(scene_id, db)


@router.post("/resync-bulk", response_model=Dict[str, Any])
async def resync_scenes_bulk(
    scene_ids: List[str] = Body(..., description="List of scene IDs to resync"),
    background: bool = Query(True, description="Run as background job"),
    job_service: JobService = Depends(get_job_service),
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Resync multiple scenes from Stash.

    This endpoint allows bulk resyncing of scenes by their IDs.
    By default, it runs as a background job for better performance.
    """
    # Validate that all scenes exist
    query = select(Scene.id).where(Scene.id.in_(scene_ids))
    result = await db.execute(query)
    existing_ids = {str(row[0]) for row in result}

    missing_ids = set(scene_ids) - existing_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scenes not found: {', '.join(missing_ids)}",
        )

    if background:
        # Queue as background job
        job = await job_service.create_job(
            job_type=ModelJobType.SYNC_SCENES,
            db=db,
            metadata={
                "scene_ids": scene_ids,
                "force": True,  # Force resync for explicit user action
            },
        )
        # Refresh the job object to ensure all attributes are loaded
        await db.refresh(job)
        return {
            "job_id": job.id,
            "status": "queued",
            "message": f"Resync job queued for {len(scene_ids)} scenes",
        }
    else:
        # Run synchronously (not recommended for many scenes)
        sync_result = await sync_service.sync_scenes(
            scene_ids=scene_ids,
            force=True,
            db=db,  # type: ignore[arg-type]
        )
        return {
            "status": "completed",
            "total_scenes": len(scene_ids),
            "synced_scenes": sync_result.processed_items,
            "failed_scenes": sync_result.failed_items,
        }


@router.patch("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: str,
    updates: Dict[str, Any] = Body(..., description="Fields to update"),
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db),
) -> SceneResponse:
    """
    Update scene metadata.

    This endpoint updates the scene in both Stashhog's database and Stash.
    """
    # Verify scene exists
    query = select(Scene).where(Scene.id == scene_id)
    result = await db.execute(query)
    scene = result.scalar_one_or_none()

    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found"
        )

    # Update in Stash first
    stash_service = sync_service.stash_service
    await stash_service.update_scene(scene_id, updates)

    # Sync the updated scene back to our database
    await sync_service.sync_scene_by_id(scene_id)

    # Get updated scene
    await db.refresh(scene)

    # Return updated scene
    return await get_scene(scene_id, db)


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_scene_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get scene statistics summary.
    """
    # Get total scenes
    total_query = select(func.count(Scene.id))
    total_result = await db.execute(total_query)
    total_scenes = total_result.scalar_one()

    # Get organized scenes
    organized_query = select(func.count(Scene.id)).where(Scene.organized.is_(True))
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
        "organization_percentage": (
            (organized_scenes / total_scenes * 100) if total_scenes > 0 else 0
        ),
        "total_tags": total_tags,
        "total_performers": total_performers,
        "total_studios": total_studios,
        "scenes_by_studio": scenes_by_studio,
    }
