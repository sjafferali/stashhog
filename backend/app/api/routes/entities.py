"""
Entity management endpoints for performers, tags, and studios.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    PaginatedResponse,
    PerformerResponse,
    StudioResponse,
    TagResponse,
)
from app.core.dependencies import get_db
from app.models import Performer, Scene, SceneMarker, Studio, Tag

router = APIRouter()


@router.get("/performers", response_model=PaginatedResponse[PerformerResponse])
async def list_performers(
    search: Optional[str] = Query(None, description="Search performers by name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PerformerResponse]:
    """
    List all performers with pagination.
    """
    # Build base query
    base_query = select(Performer)

    if search:
        base_query = base_query.where(Performer.name.ilike(f"%{search}%"))

    # Count total items
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting
    if sort_by == "name":
        order_col = Performer.name
    elif sort_by == "scene_count":
        # For scene_count sorting, we'll handle it differently
        order_col = Performer.name  # Default to name for now
    else:
        order_col = Performer.name

    if sort_order == "desc":
        base_query = base_query.order_by(order_col.desc())
    else:
        base_query = base_query.order_by(order_col)

    # Apply pagination
    offset = (page - 1) * per_page
    base_query = base_query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(base_query)
    performers = result.scalars().all()

    # Get scene counts for each performer
    performer_responses = []
    for performer in performers:
        # Count scenes for this performer
        count_query = (
            select(func.count(Scene.id))
            .join(Scene.performers)
            .where(Performer.id == performer.id)
        )
        count_result = await db.execute(count_query)
        scene_count = count_result.scalar_one()

        performer_responses.append(
            PerformerResponse(
                id=str(performer.id),
                name=str(performer.name),
                scene_count=scene_count,
                gender=performer.gender,
                favorite=(
                    performer.favorite if hasattr(performer, "favorite") else False
                ),
                rating100=(
                    performer.rating100 if hasattr(performer, "rating100") else None
                ),
            )
        )

    return PaginatedResponse.create(
        items=performer_responses, total=total, page=page, per_page=per_page
    )


@router.get("/tags", response_model=PaginatedResponse[TagResponse])
async def list_tags(
    search: Optional[str] = Query(None, description="Search tags by name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TagResponse]:
    """
    List all tags with pagination.
    """
    # Build base query
    base_query = select(Tag)

    if search:
        base_query = base_query.where(Tag.name.ilike(f"%{search}%"))

    # Count total items
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting
    if sort_by == "name":
        order_col = Tag.name
    else:
        order_col = Tag.name

    if sort_order == "desc":
        base_query = base_query.order_by(order_col.desc())
    else:
        base_query = base_query.order_by(order_col)

    # Apply pagination
    offset = (page - 1) * per_page
    base_query = base_query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(base_query)
    tags = result.scalars().all()

    # Get scene and marker counts for each tag
    tag_responses = []
    for tag in tags:
        # Count scenes for this tag
        count_query = (
            select(func.count(Scene.id)).join(Scene.tags).where(Tag.id == tag.id)
        )
        count_result = await db.execute(count_query)
        scene_count = count_result.scalar_one()

        # Count markers for this tag (both as primary tag and in tags relationship)
        # Count as primary tag
        primary_marker_query = select(func.count(SceneMarker.id)).where(
            SceneMarker.primary_tag_id == tag.id
        )
        primary_result = await db.execute(primary_marker_query)
        primary_count = primary_result.scalar_one()

        # Count through many-to-many relationship
        from app.models.scene_marker import scene_marker_tags

        secondary_marker_query = select(
            func.count(scene_marker_tags.c.scene_marker_id)
        ).where(scene_marker_tags.c.tag_id == tag.id)
        secondary_result = await db.execute(secondary_marker_query)
        secondary_count = secondary_result.scalar_one()

        # Use the maximum to avoid double counting if a tag is both primary and in the tags list
        marker_count = max(primary_count, secondary_count)

        tag_responses.append(
            TagResponse(
                id=str(tag.id),
                name=str(tag.name),
                scene_count=scene_count,
                marker_count=marker_count,
            )
        )

    return PaginatedResponse.create(
        items=tag_responses, total=total, page=page, per_page=per_page
    )


@router.get("/studios", response_model=PaginatedResponse[StudioResponse])
async def list_studios(
    search: Optional[str] = Query(None, description="Search studios by name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StudioResponse]:
    """
    List all studios with pagination.
    """
    # Build base query
    base_query = select(Studio)

    if search:
        base_query = base_query.where(Studio.name.ilike(f"%{search}%"))

    # Count total items
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting
    if sort_by == "name":
        order_col = Studio.name
    else:
        order_col = Studio.name

    if sort_order == "desc":
        base_query = base_query.order_by(order_col.desc())
    else:
        base_query = base_query.order_by(order_col)

    # Apply pagination
    offset = (page - 1) * per_page
    base_query = base_query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(base_query)
    studios = result.scalars().all()

    # Get scene counts for each studio
    studio_responses = []
    for studio in studios:
        # Count scenes for this studio
        count_query = select(func.count(Scene.id)).where(Scene.studio_id == studio.id)
        count_result = await db.execute(count_query)
        scene_count = count_result.scalar_one()

        studio_responses.append(
            StudioResponse(
                id=str(studio.id), name=str(studio.name), scene_count=scene_count
            )
        )

    return PaginatedResponse.create(
        items=studio_responses, total=total, page=page, per_page=per_page
    )


# Detail endpoints for individual entities
@router.get("/performers/{performer_id}")
async def get_performer(
    performer_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed information about a specific performer.
    """
    # Get performer with all relationships
    query = select(Performer).where(Performer.id == performer_id)
    result = await db.execute(query)
    performer = result.scalar_one_or_none()

    if not performer:
        raise HTTPException(status_code=404, detail="Performer not found")

    # Count scenes for this performer
    count_query = (
        select(func.count(Scene.id))
        .join(Scene.performers)
        .where(Performer.id == performer.id)
    )
    count_result = await db.execute(count_query)
    scene_count = count_result.scalar_one()

    return {
        "id": str(performer.id),
        "name": performer.name,
        "gender": performer.gender,
        "birthdate": performer.birthdate,
        "ethnicity": performer.ethnicity,
        "country": performer.country,
        "eye_color": performer.eye_color,
        "height": performer.height_cm,
        "measurements": performer.measurements,
        "fake_tits": performer.fake_tits,
        "tattoos": performer.tattoos,
        "piercings": performer.piercings,
        "aliases": performer.aliases,
        "favorite": performer.favorite if hasattr(performer, "favorite") else False,
        "details": performer.details,
        "hair_color": performer.hair_color,
        "weight": performer.weight_kg,
        "url": performer.url,
        "twitter": performer.twitter,
        "instagram": performer.instagram,
        "rating100": performer.rating100 if hasattr(performer, "rating100") else None,
        "scene_count": scene_count,
        "created_at": (
            performer.created_at.isoformat() if performer.created_at else None
        ),
        "updated_at": (
            performer.updated_at.isoformat() if performer.updated_at else None
        ),
    }


@router.get("/tags/{tag_id}")
async def get_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed information about a specific tag.
    """
    # Get tag
    query = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(query)
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Count scenes for this tag
    count_query = select(func.count(Scene.id)).join(Scene.tags).where(Tag.id == tag.id)
    count_result = await db.execute(count_query)
    scene_count = count_result.scalar_one()

    # Count markers for this tag (both as primary tag and in tags relationship)
    # Count as primary tag
    primary_marker_query = select(func.count(SceneMarker.id)).where(
        SceneMarker.primary_tag_id == tag.id
    )
    primary_result = await db.execute(primary_marker_query)
    primary_count = primary_result.scalar_one()

    # Count through many-to-many relationship
    from app.models.scene_marker import scene_marker_tags

    secondary_marker_query = select(
        func.count(scene_marker_tags.c.scene_marker_id)
    ).where(scene_marker_tags.c.tag_id == tag.id)
    secondary_result = await db.execute(secondary_marker_query)
    secondary_count = secondary_result.scalar_one()

    # Use the maximum to avoid double counting if a tag is both primary and in the tags list
    marker_count = max(primary_count, secondary_count)

    # Get parent and child tags if they exist
    parent_tags = []
    child_tags = []

    if hasattr(tag, "parent_tags"):
        for parent in tag.parent_tags:
            parent_tags.append({"id": str(parent.id), "name": parent.name})

    if hasattr(tag, "child_tags"):
        for child in tag.child_tags:
            child_tags.append({"id": str(child.id), "name": child.name})

    return {
        "id": str(tag.id),
        "name": tag.name,
        "aliases": tag.aliases if hasattr(tag, "aliases") else [],
        "scene_count": scene_count,
        "marker_count": marker_count,
        "parent_tags": parent_tags,
        "child_tags": child_tags,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        "updated_at": tag.updated_at.isoformat() if tag.updated_at else None,
    }


@router.get("/studios/{studio_id}")
async def get_studio(
    studio_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed information about a specific studio.
    """
    # Get studio
    query = select(Studio).where(Studio.id == studio_id)
    result = await db.execute(query)
    studio = result.scalar_one_or_none()

    if not studio:
        raise HTTPException(status_code=404, detail="Studio not found")

    # Count scenes for this studio
    count_query = select(func.count(Scene.id)).where(Scene.studio_id == studio.id)
    count_result = await db.execute(count_query)
    scene_count = count_result.scalar_one()

    # Get parent studio if exists
    parent_studio = None
    if hasattr(studio, "parent_studio_id") and studio.parent_studio_id:
        parent_query = select(Studio).where(Studio.id == studio.parent_studio_id)
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()
        if parent:
            parent_studio = {"id": str(parent.id), "name": parent.name}

    return {
        "id": str(studio.id),
        "name": studio.name,
        "url": studio.url,
        "details": studio.details,
        "scene_count": scene_count,
        "parent_studio": parent_studio,
        "rating100": studio.rating100 if hasattr(studio, "rating100") else None,
        "created_at": studio.created_at.isoformat() if studio.created_at else None,
        "updated_at": studio.updated_at.isoformat() if studio.updated_at else None,
    }
