"""
Scene management endpoints.
"""

import logging
import os
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, distinct, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    JobInfo,
    PaginatedResponse,
    PaginationParams,
    PerformerResponse,
    SceneFileResponse,
    SceneFilter,
    SceneMarkerResponse,
    SceneResponse,
    StudioResponse,
    TagResponse,
)
from app.core.dependencies import get_db, get_job_service, get_sync_service
from app.models import Performer, Scene, SceneFile, SceneMarker, Studio, SyncLog, Tag
from app.models.job import JobType as ModelJobType
from app.models.sync_history import SyncHistory
from app.repositories.job_repository import job_repository
from app.services.job_service import JobService
from app.services.sync.sync_service import SyncService

logger = logging.getLogger(__name__)
router = APIRouter()


# Response models for tag operations
class BulkTagOperationRequest(BaseModel):
    """Request model for bulk tag operations."""

    scene_ids: List[int]
    tag_ids: List[int]


class BulkTagOperationResponse(BaseModel):
    """Response model for bulk tag operations."""

    success: bool
    message: str
    scenes_updated: int
    tags_affected: int


async def parse_scene_filters(
    search: Optional[str] = Query(None),
    scene_ids: Annotated[Optional[List[str]], Query()] = None,
    studio_id: Optional[str] = Query(None),
    performer_ids: Annotated[Optional[List[str]], Query()] = None,
    tag_ids: Annotated[Optional[List[str]], Query()] = None,
    exclude_tag_ids: Annotated[Optional[List[str]], Query()] = None,
    organized: Optional[bool] = Query(None),
    analyzed: Optional[bool] = Query(None),
    video_analyzed: Optional[bool] = Query(None),
    generated: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    has_active_jobs: Optional[bool] = Query(None),
) -> SceneFilter:
    """Parse scene filters from query parameters."""
    from datetime import datetime

    # Parse dates if provided
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            pass
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            pass

    return SceneFilter(
        search=search,
        scene_ids=scene_ids or [],
        studio_id=studio_id,
        performer_ids=performer_ids or [],
        tag_ids=tag_ids or [],
        exclude_tag_ids=exclude_tag_ids or [],
        organized=organized,
        analyzed=analyzed,
        video_analyzed=video_analyzed,
        generated=generated,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        has_active_jobs=has_active_jobs,
    )


def _build_scene_filter_conditions(
    filters: SceneFilter, query: Any
) -> tuple[Any, list[Any]]:
    """Build filter conditions for scene query."""
    conditions: list[Any] = []

    # Apply search filter
    query, conditions = _apply_search_filter(filters, query, conditions)

    # Apply ID-based filters
    query, conditions = _apply_id_filters(filters, query, conditions)

    # Apply boolean filters
    conditions = _apply_boolean_filters(filters, conditions)

    # Apply date filters
    conditions = _apply_date_filters(filters, conditions)

    return query, conditions


def _apply_search_filter(
    filters: SceneFilter, query: Any, conditions: list[Any]
) -> tuple[Any, list[Any]]:
    """Apply search filter to query."""
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.outerjoin(Scene.files)
        conditions.append(
            or_(
                Scene.title.ilike(search_term),
                Scene.details.ilike(search_term),
                SceneFile.path.ilike(search_term),
            )
        )
    return query, conditions


def _apply_id_filters(
    filters: SceneFilter, query: Any, conditions: list[Any]
) -> tuple[Any, list[Any]]:
    """Apply ID-based filters to query."""
    if filters.scene_ids:
        conditions.append(Scene.id.in_(filters.scene_ids))

    if filters.studio_id:
        conditions.append(Scene.studio_id == filters.studio_id)

    if filters.performer_ids:
        query = query.join(Scene.performers)
        conditions.append(Performer.id.in_(filters.performer_ids))

    if filters.tag_ids:
        query = query.join(Scene.tags)
        conditions.append(Tag.id.in_(filters.tag_ids))

    if filters.exclude_tag_ids:
        excluded_scenes = (
            select(Scene.id)
            .join(Scene.tags)
            .where(Tag.id.in_(filters.exclude_tag_ids))
            .distinct()
        )
        conditions.append(~Scene.id.in_(excluded_scenes))

    return query, conditions


def _apply_boolean_filters(filters: SceneFilter, conditions: list[Any]) -> list[Any]:
    """Apply boolean filters to conditions."""
    if filters.organized is not None:
        conditions.append(Scene.organized == filters.organized)

    if filters.analyzed is not None:
        conditions.append(Scene.analyzed == filters.analyzed)

    if filters.video_analyzed is not None:
        conditions.append(Scene.video_analyzed == filters.video_analyzed)

    if filters.generated is not None:
        conditions.append(Scene.generated == filters.generated)

    return conditions


def _apply_date_filters(filters: SceneFilter, conditions: list[Any]) -> list[Any]:
    """Apply date filters to conditions."""
    if filters.date_from:
        conditions.append(Scene.stash_date >= filters.date_from)

    if filters.date_to:
        conditions.append(Scene.stash_date <= filters.date_to)

    return conditions


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


def _transform_job_to_info(job) -> JobInfo:
    """Transform Job model to JobInfo."""
    return JobInfo(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        started_at=job.started_at,
    )


def _transform_scene_to_response(scene: Scene) -> SceneResponse:
    """Transform Scene model to SceneResponse."""
    # Get primary file for metadata
    primary_file = scene.get_primary_file()

    # Use filename if title is empty or blank
    title = scene.title
    if not title or not title.strip():
        # Use primary file path if available
        if primary_file and primary_file.path:
            title = os.path.basename(primary_file.path)

    # Build paths array and file_path for backward compatibility
    paths = []
    file_path = None
    if hasattr(scene, "files") and scene.files:
        paths = [f.path for f in scene.files if f.path]
        if primary_file:
            file_path = primary_file.path

    return SceneResponse(
        id=scene.id,  # type: ignore[arg-type]
        title=title,  # type: ignore[arg-type]
        paths=paths,  # type: ignore[arg-type]
        file_path=file_path,  # type: ignore[arg-type]
        organized=scene.organized,  # type: ignore[arg-type]
        analyzed=scene.analyzed,  # type: ignore[arg-type]
        video_analyzed=scene.video_analyzed,  # type: ignore[arg-type]
        generated=scene.generated,  # type: ignore[arg-type]
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
            PerformerResponse(
                id=p.id,
                name=p.name,
                scene_count=0,
                gender=getattr(p, "gender", None),
                favorite=getattr(p, "favorite", False),
                rating100=getattr(
                    p, "rating", None
                ),  # Convert rating to rating100 if needed
            )
            for p in scene.performers
        ],
        tags=[TagResponse(id=t.id, name=t.name, scene_count=0) for t in scene.tags],
        markers=[
            SceneMarkerResponse(
                id=m.id,
                title=m.title,
                seconds=m.seconds,
                end_seconds=m.end_seconds,
                primary_tag=TagResponse(
                    id=m.primary_tag.id, name=m.primary_tag.name, scene_count=0
                ),
                tags=[TagResponse(id=t.id, name=t.name, scene_count=0) for t in m.tags],
                created_at=m.stash_created_at,
                updated_at=m.stash_updated_at,
            )
            for m in scene.markers
        ],
        files=(
            [
                SceneFileResponse(
                    id=f.id,
                    path=f.path,
                    basename=f.basename,
                    is_primary=f.is_primary,
                    size=f.size,
                    format=f.format,
                    duration=f.duration,
                    width=f.width,
                    height=f.height,
                    video_codec=f.video_codec,
                    audio_codec=f.audio_codec,
                    frame_rate=f.frame_rate,
                    bit_rate=f.bit_rate,
                    oshash=f.oshash,
                    phash=f.phash,
                    mod_time=f.mod_time,
                )
                for f in scene.files
            ]
            if hasattr(scene, "files")
            else []
        ),
        last_synced=scene.last_synced,  # type: ignore[arg-type]
        created_at=scene.created_at,  # type: ignore[arg-type]
        updated_at=scene.updated_at,  # type: ignore[arg-type]
        # Metadata fields - populate from primary file for backward compatibility
        duration=primary_file.duration if primary_file else None,  # type: ignore[arg-type]
        size=primary_file.size if primary_file else None,  # type: ignore[arg-type]
        width=primary_file.width if primary_file else None,  # type: ignore[arg-type]
        height=primary_file.height if primary_file else None,  # type: ignore[arg-type]
        framerate=primary_file.frame_rate if primary_file else None,  # type: ignore[arg-type]
        bitrate=primary_file.bit_rate if primary_file else None,  # type: ignore[arg-type]
        video_codec=primary_file.video_codec if primary_file else None,  # type: ignore[arg-type]
        # Job fields - will be populated later if needed
        active_jobs=[],  # type: ignore[arg-type]
        recent_jobs=[],  # type: ignore[arg-type]
    )


@router.get("", response_model=PaginatedResponse[SceneResponse])
async def list_scenes(
    pagination: PaginationParams = Depends(),
    filters: SceneFilter = Depends(parse_scene_filters),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SceneResponse]:
    """
    List scenes with pagination and filters.
    """
    # Build base query
    query = select(Scene).distinct()

    # Apply filters
    query, conditions = _build_scene_filter_conditions(filters, query)

    # Handle has_active_jobs filter at database level
    if filters.has_active_jobs is not None:
        # Get all scene IDs that have active jobs
        jobs_with_scenes = await job_repository.get_all_active_job_scene_ids(db)

        if filters.has_active_jobs:
            # Include only scenes that have active jobs
            if jobs_with_scenes:
                conditions.append(Scene.id.in_(jobs_with_scenes))
            else:
                # No active jobs exist, so return empty result
                conditions.append(Scene.id.is_(None))  # This will match no scenes
        else:
            # Exclude scenes that have active jobs
            if jobs_with_scenes:
                conditions.append(~Scene.id.in_(jobs_with_scenes))

    if conditions:
        query = query.where(and_(*conditions))

    # Add eager loading options
    query = query.options(
        selectinload(Scene.performers),
        selectinload(Scene.tags),
        selectinload(Scene.studio),
        selectinload(Scene.markers).selectinload(SceneMarker.primary_tag),
        selectinload(Scene.markers).selectinload(SceneMarker.tags),
        selectinload(Scene.files),
    )

    # Apply sorting
    query = _apply_scene_sorting(query, pagination)

    # Count total distinct scenes (important when joining with tags/performers)
    # Create a count query that counts distinct scene IDs
    count_subquery = query.subquery()
    count_query = select(func.count(distinct(count_subquery.c.id)))
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    query = query.offset((pagination.page - 1) * pagination.per_page).limit(
        pagination.per_page
    )

    # Execute query
    result = await db.execute(query)
    scenes = result.scalars().unique().all()

    # Fetch job information for all scenes
    scene_ids = [str(scene.id) for scene in scenes]  # type: ignore[attr-defined]
    active_jobs = (
        await job_repository.get_active_jobs_for_scenes(scene_ids, db)
        if scene_ids
        else {}
    )
    recent_jobs = (
        await job_repository.get_recent_jobs_for_scenes(scene_ids, db)
        if scene_ids
        else {}
    )

    # Transform to response models with job information
    scene_responses = []
    for scene in scenes:
        response = _transform_scene_to_response(scene)  # type: ignore[arg-type]
        # Add job information
        response.active_jobs = [
            _transform_job_to_info(job) for job in active_jobs.get(str(scene.id), [])  # type: ignore[attr-defined]
        ]
        response.recent_jobs = [
            _transform_job_to_info(job) for job in recent_jobs.get(str(scene.id), [])  # type: ignore[attr-defined]
        ]
        scene_responses.append(response)

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
            selectinload(Scene.markers).selectinload(SceneMarker.primary_tag),
            selectinload(Scene.markers).selectinload(SceneMarker.tags),
            selectinload(Scene.files),
        )
        .where(Scene.id == scene_id)
    )

    result = await db.execute(query)
    scene = result.scalar_one_or_none()

    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found"
        )

    # Get job information for this scene
    active_jobs = await job_repository.get_active_jobs_for_scenes([scene_id], db)
    recent_jobs = await job_repository.get_recent_jobs_for_scenes([scene_id], db)

    # Transform to response model
    response = _transform_scene_to_response(scene)
    response.active_jobs = [
        _transform_job_to_info(job) for job in active_jobs.get(scene_id, [])
    ]
    response.recent_jobs = [
        _transform_job_to_info(job) for job in recent_jobs.get(scene_id, [])
    ]

    return response


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


@router.patch("/bulk-update", response_model=Dict[str, Any])
async def bulk_update_scenes(
    scene_ids: List[str] = Body(..., description="List of scene IDs to update"),
    updates: Dict[str, Any] = Body(..., description="Fields to update"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Bulk update scene attributes.

    This endpoint allows updating multiple scenes with the same attributes.
    Currently supports updating 'analyzed', 'video_analyzed', and 'generated' fields.
    """
    # Validate that only allowed fields are being updated
    allowed_fields = {"analyzed", "video_analyzed", "generated"}
    update_fields = set(updates.keys())
    invalid_fields = update_fields - allowed_fields

    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields for bulk update: {invalid_fields}. Allowed fields: {allowed_fields}",
        )

    # Update scenes in database (scene IDs are strings in the database)
    update_stmt = update(Scene).where(Scene.id.in_(scene_ids)).values(**updates)

    result = await db.execute(update_stmt)
    await db.commit()

    # Get updated count
    updated_count = result.rowcount

    return {"updated_count": updated_count, "scene_ids": scene_ids, "updates": updates}


@router.post("/add-tags", response_model=BulkTagOperationResponse)
async def add_tags_to_scenes(
    request: BulkTagOperationRequest = Body(..., description="Scene and tag IDs"),
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db),
) -> BulkTagOperationResponse:
    """
    Add tags to multiple scenes.

    This endpoint adds the specified tags to all provided scenes, updating both
    the local Stashhog database and the Stash instance.

    Args:
        request: Contains scene_ids and tag_ids to process
        sync_service: Service for syncing with Stash
        db: Database session

    Returns:
        BulkTagOperationResponse with operation results

    Raises:
        HTTPException 404: If no scenes or tags found with provided IDs
    """
    # Convert scene_ids to strings since our DB uses string IDs
    scene_id_strings = [str(sid) for sid in request.scene_ids]

    # Convert tag_ids to strings since our DB uses string IDs
    tag_id_strings = [str(tid) for tid in request.tag_ids]

    # Get all scenes with their existing tags
    scenes_query = (
        select(Scene)
        .where(Scene.id.in_(scene_id_strings))
        .options(selectinload(Scene.tags))
    )
    scenes_result = await db.execute(scenes_query)
    scenes = scenes_result.scalars().all()

    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scenes found with provided IDs",
        )

    # Get tags to add
    tags_query = select(Tag).where(Tag.id.in_(tag_id_strings))
    tags_result = await db.execute(tags_query)
    tags_to_add = tags_result.scalars().all()

    if not tags_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tags found with provided IDs",
        )

    stash_service = sync_service.stash_service
    scenes_updated = 0

    # Process each scene
    for scene in scenes:
        # Get current tag IDs
        current_tag_ids = [tag.id for tag in scene.tags]

        # Determine which tags are new
        new_tags = [tag for tag in tags_to_add if tag not in scene.tags]

        if new_tags:
            # Add tags to local database
            for tag in new_tags:
                scene.tags.append(tag)

            # Prepare tag IDs for Stash update (all current + new)
            all_tag_ids = current_tag_ids + [tag.id for tag in new_tags]

            # Update scene in Stash
            try:
                await stash_service.update_scene(
                    str(scene.id), {"tag_ids": all_tag_ids}
                )
                scenes_updated += 1
            except Exception as e:
                logger.error(f"Failed to update scene {scene.id} in Stash: {e}")
                # Continue with other scenes even if one fails

    # Commit database changes
    await db.commit()

    return BulkTagOperationResponse(
        success=True,
        message=f"Successfully added {len(tags_to_add)} tag(s) to {scenes_updated} scene(s)",
        scenes_updated=scenes_updated,
        tags_affected=len(tags_to_add),
    )


@router.post("/remove-tags", response_model=BulkTagOperationResponse)
async def remove_tags_from_scenes(
    request: BulkTagOperationRequest = Body(..., description="Scene and tag IDs"),
    sync_service: SyncService = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db),
) -> BulkTagOperationResponse:
    """
    Remove tags from multiple scenes.

    This endpoint removes the specified tags from all provided scenes, updating both
    the local Stashhog database and the Stash instance.

    Args:
        request: Contains scene_ids and tag_ids to process
        sync_service: Service for syncing with Stash
        db: Database session

    Returns:
        BulkTagOperationResponse with operation results

    Raises:
        HTTPException 404: If no scenes found with provided IDs
    """
    # Convert scene_ids to strings since our DB uses string IDs
    scene_id_strings = [str(sid) for sid in request.scene_ids]

    # Get all scenes with their tags
    scenes_query = (
        select(Scene)
        .where(Scene.id.in_(scene_id_strings))
        .options(selectinload(Scene.tags))
    )
    scenes_result = await db.execute(scenes_query)
    scenes = scenes_result.scalars().all()

    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scenes found with provided IDs",
        )

    stash_service = sync_service.stash_service
    scenes_updated = 0

    # Convert tag IDs to strings since our DB uses string IDs
    tag_id_strings = [str(tid) for tid in request.tag_ids]

    # Process each scene
    for scene in scenes:
        initial_tag_count = len(scene.tags)

        # Remove tags from local database
        scene.tags = [tag for tag in scene.tags if tag.id not in tag_id_strings]

        if len(scene.tags) < initial_tag_count:
            # Get remaining tag IDs for Stash update
            remaining_tag_ids = [tag.id for tag in scene.tags]

            # Update scene in Stash
            try:
                await stash_service.update_scene(
                    str(scene.id), {"tag_ids": remaining_tag_ids}
                )
                scenes_updated += 1
            except Exception as e:
                logger.error(f"Failed to update scene {scene.id} in Stash: {e}")
                # Continue with other scenes even if one fails

    # Commit database changes
    await db.commit()

    return BulkTagOperationResponse(
        success=True,
        message=f"Successfully removed {len(request.tag_ids)} tag(s) from {scenes_updated} scene(s)",
        scenes_updated=scenes_updated,
        tags_affected=len(request.tag_ids),
    )


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
    # Get scene with proper session tracking
    scene = await db.get(Scene, scene_id)

    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found"
        )

    # Log the incoming updates for debugging
    logger.info(f"Updating scene {scene_id} with updates: {updates}")

    # Separate StashHog-specific fields from Stash fields
    stashhog_fields = {"analyzed", "video_analyzed", "generated"}
    stashhog_updates = {k: v for k, v in updates.items() if k in stashhog_fields}
    stash_updates = {k: v for k, v in updates.items() if k not in stashhog_fields}

    logger.info(f"StashHog updates: {stashhog_updates}, Stash updates: {stash_updates}")

    # Update StashHog-specific fields locally
    if stashhog_updates:
        for field, value in stashhog_updates.items():
            logger.info(f"Setting scene.{field} = {value}")
            setattr(scene, field, value)

        # Commit the changes
        await db.commit()
        logger.info(f"Committed StashHog updates for scene {scene_id}")

        # Refresh the scene object to get the committed state
        await db.refresh(scene)
        logger.info(f"After refresh - scene.generated = {scene.generated}")

    # Update Stash fields if any
    if stash_updates:
        stash_service = sync_service.stash_service
        await stash_service.update_scene(scene_id, stash_updates)

        # Sync the updated scene back to our database
        await sync_service.sync_scene_by_id(scene_id)

        # Refresh again after Stash sync
        await db.refresh(scene)

    # Return updated scene - use the already refreshed scene object
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


@router.get("/{scene_id}/sync-logs", response_model=List[Dict[str, Any]])
async def get_scene_sync_logs(
    scene_id: str,
    limit: int = Query(50, description="Maximum number of logs to return"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Get sync history logs for a specific scene.

    Returns sync logs where the scene was specifically synced (entity_id matches).
    This includes:
    - Individual scene syncs
    - Scene updates during incremental syncs
    - Scene processing during full syncs (each scene gets its own log entry)
    """
    # Query sync logs for this scene
    query = (
        select(SyncLog, SyncHistory)
        .join(SyncHistory, SyncLog.sync_history_id == SyncHistory.id)
        .where(SyncLog.entity_id == scene_id)
        .order_by(SyncLog.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    sync_logs = result.all()

    return [
        {
            "id": log.SyncLog.id,
            "sync_type": log.SyncLog.sync_type,
            "had_changes": log.SyncLog.had_changes,
            "change_type": log.SyncLog.change_type,
            "error_message": log.SyncLog.error_message,
            "created_at": log.SyncLog.created_at,
            "sync_history": {
                "job_id": log.SyncHistory.job_id,
                "started_at": log.SyncHistory.started_at,
                "completed_at": log.SyncHistory.completed_at,
                "status": log.SyncHistory.status,
                "items_synced": log.SyncHistory.items_synced,
                "items_created": log.SyncHistory.items_created,
                "items_updated": log.SyncHistory.items_updated,
            },
        }
        for log in sync_logs
    ]
