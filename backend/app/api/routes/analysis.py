"""
Analysis operations endpoints.
"""
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.api.schemas import (
    AnalysisRequest,
    PlanResponse,
    PlanDetailResponse,
    SceneChanges,
    ChangePreview,
    PaginatedResponse,
    SuccessResponse,
    PaginationParams,
    SceneFilter
)
from app.core.dependencies import get_db, get_job_queue, get_analysis_service
from app.core.exceptions import ResourceNotFoundError
from app.services.analysis_service import AnalysisService
from app.services.job_queue import JobQueue
from app.models import AnalysisPlan, PlanChange, Scene
from app.models.job import JobType

router = APIRouter()


@router.post("/generate")
async def generate_analysis(
    request: AnalysisRequest,
    background: bool = Query(True, description="Run as background job"),
    job_queue: JobQueue = Depends(get_job_queue),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate analysis plan for scenes.
    
    Can analyze specific scenes by ID or use filters to select scenes.
    """
    # Validate scene selection
    if not request.scene_ids and not request.filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either scene_ids or filters must be provided"
        )
    
    # If using filters, get scene IDs
    scene_ids = request.scene_ids
    if not scene_ids and request.filters:
        # Build query from filters
        query = select(Scene.id)
        conditions = []
        
        if request.filters.search:
            search_term = f"%{request.filters.search}%"
            conditions.append(
                or_(
                    Scene.title.ilike(search_term),
                    Scene.details.ilike(search_term)
                )
            )
        
        if request.filters.studio_id:
            conditions.append(Scene.studio_id == request.filters.studio_id)
        
        if request.filters.organized is not None:
            conditions.append(Scene.organized == request.filters.organized)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        scene_ids = [row[0] for row in result]
    
    if not scene_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No scenes found matching the criteria"
        )
    
    if background:
        # Queue as background job
        job_id = await job_queue.enqueue(
            job_type=JobType.BATCH_ANALYSIS,
            params={
                "scene_ids": scene_ids,
                "options": request.options.model_dump(),
                "plan_name": request.plan_name
            }
        )
        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"Analysis job queued for {len(scene_ids)} scenes"
        }
    else:
        # Run synchronously (not recommended for large batches)
        plan = await analysis_service.analyze_scenes(
            scene_ids=scene_ids,
            options=request.options,
            plan_name=request.plan_name
        )
        return {
            "plan_id": plan.id,
            "status": "completed",
            "total_scenes": len(scene_ids),
            "total_changes": plan.total_changes
        }


@router.get("/plans", response_model=PaginatedResponse[PlanResponse])
async def list_plans(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Filter by plan status"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[PlanResponse]:
    """
    List analysis plans.
    """
    # Build query
    query = select(AnalysisPlan)
    
    if status:
        query = query.where(AnalysisPlan.status == status)
    
    # Apply sorting
    query = query.order_by(AnalysisPlan.created_at.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Apply pagination
    query = query.offset((pagination.page - 1) * pagination.per_page).limit(pagination.per_page)
    
    # Execute query
    result = await db.execute(query)
    plans = result.scalars().all()
    
    # Convert to response objects
    plan_responses = []
    for plan in plans:
        # Count changes
        change_count_query = select(func.count(PlanChange.id)).where(PlanChange.plan_id == plan.id)
        change_result = await db.execute(change_count_query)
        total_changes = change_result.scalar_one()
        
        # Count scenes
        scene_count_query = select(func.count(func.distinct(PlanChange.scene_id))).where(PlanChange.plan_id == plan.id)
        scene_result = await db.execute(scene_count_query)
        total_scenes = scene_result.scalar_one()
        
        plan_responses.append(PlanResponse(
            id=plan.id,
            name=plan.name,
            status=plan.status,
            created_at=plan.created_at,
            total_scenes=total_scenes,
            total_changes=total_changes,
            metadata=plan.metadata or {}
        ))
    
    return PaginatedResponse.create(
        items=plan_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page
    )


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
) -> PlanDetailResponse:
    """
    Get plan with all changes.
    """
    # Get the plan
    query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis plan {plan_id} not found"
        )
    
    # Get all changes grouped by scene
    changes_query = (
        select(PlanChange, Scene)
        .join(Scene, PlanChange.scene_id == Scene.id)
        .where(PlanChange.plan_id == plan_id)
        .order_by(PlanChange.scene_id, PlanChange.field)
    )
    result = await db.execute(changes_query)
    changes_with_scenes = result.all()
    
    # Group changes by scene
    scenes_dict = {}
    for change, scene in changes_with_scenes:
        if scene.id not in scenes_dict:
            scenes_dict[scene.id] = {
                "scene_id": scene.id,
                "scene_title": scene.title,
                "changes": []
            }
        
        scenes_dict[scene.id]["changes"].append(ChangePreview(
            field=change.field,
            action=change.action,
            current_value=change.current_value,
            proposed_value=change.proposed_value,
            confidence=change.confidence
        ))
    
    # Convert to SceneChanges objects
    scenes = [
        SceneChanges(**scene_data)
        for scene_data in scenes_dict.values()
    ]
    
    # Count totals
    total_changes = sum(len(s.changes) for s in scenes)
    
    return PlanDetailResponse(
        id=plan.id,
        name=plan.name,
        status=plan.status,
        created_at=plan.created_at,
        total_scenes=len(scenes),
        total_changes=total_changes,
        metadata=plan.metadata or {},
        scenes=scenes
    )


@router.post("/plans/{plan_id}/apply")
async def apply_plan(
    plan_id: int,
    scene_ids: Optional[List[str]] = Query(None, description="Apply to specific scenes only"),
    background: bool = Query(True, description="Run as background job"),
    job_queue: JobQueue = Depends(get_job_queue),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Apply plan changes.
    
    Can apply to all scenes in the plan or specific scenes only.
    """
    # Verify plan exists
    query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis plan {plan_id} not found"
        )
    
    # Check if plan is already applied
    if plan.status == "applied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan has already been applied"
        )
    
    if background:
        # Queue as background job
        job_id = await job_queue.enqueue(
            job_type=JobType.APPLY_PLAN,
            params={
                "plan_id": plan_id,
                "scene_ids": scene_ids
            }
        )
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Plan application job has been queued"
        }
    else:
        # Apply synchronously
        result = await analysis_service.apply_plan(
            plan_id=plan_id,
            scene_ids=scene_ids
        )
        return {
            "status": "completed",
            "scenes_updated": result.get("scenes_updated", 0),
            "changes_applied": result.get("changes_applied", 0),
            "errors": result.get("errors", [])
        }


@router.patch("/changes/{change_id}")
async def update_change(
    change_id: int,
    proposed_value: Any,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update individual change.
    
    Allows modifying the proposed value before applying the plan.
    """
    # Get the change
    query = select(PlanChange).where(PlanChange.id == change_id)
    result = await db.execute(query)
    change = result.scalar_one_or_none()
    
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change {change_id} not found"
        )
    
    # Check if change can be modified
    if change.applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an applied change"
        )
    
    # Update the proposed value
    change.proposed_value = proposed_value
    await db.commit()
    await db.refresh(change)
    
    return {
        "id": change.id,
        "field": change.field,
        "action": change.action,
        "current_value": change.current_value,
        "proposed_value": change.proposed_value,
        "confidence": change.confidence
    }


