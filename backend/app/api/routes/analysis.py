"""
Analysis operations endpoints.
"""

from typing import Any, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AnalysisRequest,
    ChangePreview,
    PaginatedResponse,
    PaginationParams,
    PlanDetailResponse,
    PlanResponse,
    SceneChanges,
)
from app.core.dependencies import get_analysis_service, get_db, get_job_service
from app.models import AnalysisPlan, PlanChange, Scene
from app.models.job import JobType as ModelJobType
from app.services.analysis.analysis_service import AnalysisService
from app.services.job_service import JobService

router = APIRouter()


@router.get("/stats")
async def get_analysis_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get analysis statistics.

    Returns counts of analyzed scenes, plans, and pending analysis.
    """
    # Count total scenes
    total_scenes_query = select(func.count(Scene.id))
    total_scenes_result = await db.execute(total_scenes_query)
    total_scenes = total_scenes_result.scalar_one()

    # Count scenes that have been analyzed
    analyzed_scenes_query = select(func.count(Scene.id)).where(Scene.analyzed.is_(True))
    analyzed_scenes_result = await db.execute(analyzed_scenes_query)
    analyzed_scenes = analyzed_scenes_result.scalar_one()

    # Count total plans
    total_plans_query = select(func.count(AnalysisPlan.id))
    total_plans_result = await db.execute(total_plans_query)
    total_plans = total_plans_result.scalar_one()

    # Count pending plans (not applied)
    pending_plans_query = select(func.count(AnalysisPlan.id)).where(
        AnalysisPlan.status != "applied"
    )
    pending_plans_result = await db.execute(pending_plans_query)
    pending_plans = pending_plans_result.scalar_one()

    # Calculate pending analysis (scenes not analyzed)
    pending_analysis = total_scenes - analyzed_scenes

    return {
        "total_scenes": total_scenes,
        "analyzed_scenes": analyzed_scenes,
        "total_plans": total_plans,
        "pending_plans": pending_plans,
        "pending_analysis": pending_analysis,
    }


@router.post("/generate")
async def generate_analysis(
    request: AnalysisRequest,
    background: bool = Query(True, description="Run as background job"),
    job_service: JobService = Depends(get_job_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate analysis plan for scenes.

    Can analyze specific scenes by ID or use filters to select scenes.
    """
    # Validate scene selection
    if not request.scene_ids and not request.filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either scene_ids or filters must be provided",
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
                or_(Scene.title.ilike(search_term), Scene.details.ilike(search_term))
            )

        if request.filters.studio_id:
            conditions.append(Scene.studio_id == request.filters.studio_id)

        if request.filters.organized is not None:
            conditions.append(Scene.organized == request.filters.organized)

        if request.filters.analyzed is not None:
            conditions.append(Scene.analyzed == request.filters.analyzed)

        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        scene_ids = [str(row[0]) for row in result]

    if not scene_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No scenes found matching the criteria",
        )

    if background:
        # Queue as background job
        job = await job_service.create_job(
            job_type=ModelJobType.ANALYSIS,
            db=db,
            metadata={
                "scene_ids": scene_ids,
                "options": request.options.model_dump(),
                "plan_name": request.plan_name,
            },
        )
        return {
            "job_id": job.id,
            "status": "queued",
            "message": f"Analysis job queued for {len(scene_ids)} scenes",
        }
    else:
        # Run synchronously (not recommended for large batches)
        # Convert API AnalysisOptions to service AnalysisOptions
        from app.services.analysis.models import (
            AnalysisOptions as ServiceAnalysisOptions,
        )

        service_options = ServiceAnalysisOptions(
            detect_performers=request.options.detect_performers,
            detect_studios=request.options.detect_studios,
            detect_tags=request.options.detect_tags,
            detect_details=request.options.detect_details,
            use_ai=request.options.use_ai,
            confidence_threshold=request.options.confidence_threshold,
        )
        plan = await analysis_service.analyze_scenes(
            scene_ids=scene_ids, options=service_options
        )
        return {
            "plan_id": plan.id,
            "status": "completed",
            "total_scenes": len(scene_ids),
            "total_changes": plan.total_changes,
        }


@router.get("/plans", response_model=PaginatedResponse[PlanResponse])
async def list_plans(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Filter by plan status"),
    db: AsyncSession = Depends(get_db),
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
    query = query.offset((pagination.page - 1) * pagination.per_page).limit(
        pagination.per_page
    )

    # Execute query
    result = await db.execute(query)
    plans = result.scalars().all()

    # Convert to response objects
    plan_responses = []
    for plan in plans:
        # Count changes
        change_count_query = select(func.count(PlanChange.id)).where(
            PlanChange.plan_id == plan.id  # type: ignore[attr-defined]
        )
        change_result = await db.execute(change_count_query)
        total_changes = change_result.scalar_one()

        # Count scenes
        scene_count_query = select(
            func.count(func.distinct(PlanChange.scene_id))
        ).where(
            PlanChange.plan_id == plan.id  # type: ignore
        )
        scene_result = await db.execute(scene_count_query)
        total_scenes = scene_result.scalar_one()

        plan_responses.append(
            PlanResponse(
                id=plan.id,  # type: ignore[attr-defined]
                name=plan.name,  # type: ignore[attr-defined]
                status=plan.status.value if hasattr(plan.status, "value") else plan.status,  # type: ignore[attr-defined]
                created_at=plan.created_at,  # type: ignore[attr-defined]
                total_scenes=total_scenes,
                total_changes=total_changes,
                metadata=plan.plan_metadata or {},  # type: ignore[attr-defined]
            )
        )

    return PaginatedResponse.create(
        items=plan_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(
    plan_id: int, db: AsyncSession = Depends(get_db)
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
            detail=f"Analysis plan {plan_id} not found",
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
                "changes": [],
            }

        scenes_dict[scene.id]["changes"].append(
            ChangePreview(
                id=change.id,
                field=change.field,
                action=change.action,
                current_value=change.current_value,
                proposed_value=change.proposed_value,
                confidence=change.confidence,
                applied=change.applied,
                rejected=change.rejected,
            )
        )

    # Convert to SceneChanges objects
    scenes = [SceneChanges(**scene_data) for scene_data in scenes_dict.values()]

    # Count totals
    total_changes = sum(len(s.changes) for s in scenes)

    return PlanDetailResponse(
        id=int(plan.id),
        name=str(plan.name),
        status=plan.status.value if hasattr(plan.status, "value") else str(plan.status),
        created_at=plan.created_at,  # type: ignore[arg-type]
        total_scenes=len(scenes),
        total_changes=total_changes,
        metadata=dict(plan.plan_metadata) if plan.plan_metadata else {},
        scenes=scenes,
    )


@router.post("/plans/{plan_id}/apply")
async def apply_plan(
    plan_id: int,
    scene_ids: Optional[list[str]] = Query(
        None, description="Apply to specific scenes only"
    ),
    background: bool = Query(True, description="Run as background job"),
    job_service: JobService = Depends(get_job_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
            detail=f"Analysis plan {plan_id} not found",
        )

    # Check if plan is already applied
    if plan.status == "applied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan has already been applied",
        )

    if background:
        # Queue as background job
        job = await job_service.create_job(
            job_type=ModelJobType.APPLY_PLAN,
            db=db,
            metadata={"plan_id": plan_id, "scene_ids": scene_ids},
        )
        return {
            "job_id": job.id,
            "status": "queued",
            "message": "Plan application job has been queued",
        }
    else:
        # Apply synchronously
        apply_result = await analysis_service.apply_plan(plan_id=str(plan_id))
        return {
            "status": "completed",
            "scenes_updated": apply_result.scenes_analyzed,
            "changes_applied": apply_result.applied_changes,
            "errors": apply_result.errors,
        }


@router.patch("/changes/{change_id}")
async def update_change(
    change_id: int, proposed_value: Any = Body(...), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
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
            detail=f"Change {change_id} not found",
        )

    # Check if change can be modified
    if change.applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an applied change",
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
        "confidence": change.confidence,
    }


@router.patch("/changes/{change_id}/status")
async def update_change_status(
    change_id: int,
    accepted: Optional[bool] = Body(None, description="Whether the change is accepted"),
    rejected: Optional[bool] = Body(None, description="Whether the change is rejected"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update the acceptance/rejection status of a change.
    """
    # Get the change
    query = select(PlanChange).where(PlanChange.id == change_id)
    result = await db.execute(query)
    change = result.scalar_one_or_none()

    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change {change_id} not found",
        )

    # Check if change can be modified
    if change.applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an applied change",
        )

    # Update status
    if accepted is not None:
        change.applied = accepted  # type: ignore[assignment]
        if accepted:
            change.rejected = False  # type: ignore[assignment]

    if rejected is not None:
        change.rejected = rejected  # type: ignore[assignment]
        if rejected:
            change.applied = False  # type: ignore[assignment]

    # Update plan status - commit the change first
    await db.commit()

    # Refresh the change to ensure we have the latest data
    await db.refresh(change)

    # Load the plan to update status in a new query
    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == change.plan_id)
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one()

    # Update plan status and commit
    plan.update_status_based_on_changes()
    await db.commit()

    return {
        "id": change.id,
        "field": change.field,
        "action": change.action,
        "current_value": change.current_value,
        "proposed_value": change.proposed_value,
        "confidence": change.confidence,
        "applied": change.applied,
        "rejected": change.rejected,
        "plan_status": plan.status.value,
    }
