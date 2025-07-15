"""
Entity management endpoints for performers, tags, and studios.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PerformerResponse, StudioResponse, TagResponse
from app.core.dependencies import get_db
from app.models import Performer, Scene, Studio, Tag

router = APIRouter()


@router.get("/performers", response_model=List[PerformerResponse])
async def list_performers(
    search: Optional[str] = Query(None, description="Search performers by name"),
    db: AsyncSession = Depends(get_db),
) -> List[PerformerResponse]:
    """
    List all performers.
    """
    # Build query
    query = select(Performer)

    if search:
        query = query.where(Performer.name.ilike(f"%{search}%"))

    query = query.order_by(Performer.name)

    # Execute query
    result = await db.execute(query)
    performers = result.scalars().all()

    # Get scene counts
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
                id=str(performer.id), name=str(performer.name), scene_count=scene_count
            )
        )

    return performer_responses


@router.get("/tags", response_model=List[TagResponse])
async def list_tags(
    search: Optional[str] = Query(None, description="Search tags by name"),
    db: AsyncSession = Depends(get_db),
) -> List[TagResponse]:
    """
    List all tags.
    """
    # Build query
    query = select(Tag)

    if search:
        query = query.where(Tag.name.ilike(f"%{search}%"))

    query = query.order_by(Tag.name)

    # Execute query
    result = await db.execute(query)
    tags = result.scalars().all()

    # Get scene counts
    tag_responses = []
    for tag in tags:
        # Count scenes for this tag
        count_query = (
            select(func.count(Scene.id)).join(Scene.tags).where(Tag.id == tag.id)
        )
        count_result = await db.execute(count_query)
        scene_count = count_result.scalar_one()

        tag_responses.append(
            TagResponse(id=str(tag.id), name=str(tag.name), scene_count=scene_count)
        )

    return tag_responses


@router.get("/studios", response_model=List[StudioResponse])
async def list_studios(
    search: Optional[str] = Query(None, description="Search studios by name"),
    db: AsyncSession = Depends(get_db),
) -> List[StudioResponse]:
    """
    List all studios.
    """
    # Build query
    query = select(Studio)

    if search:
        query = query.where(Studio.name.ilike(f"%{search}%"))

    query = query.order_by(Studio.name)

    # Execute query
    result = await db.execute(query)
    studios = result.scalars().all()

    # Get scene counts
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

    return studio_responses
