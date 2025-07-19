"""
Analysis operations endpoints.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Sequence, cast

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
from sqlalchemy.sql import Select

from app.api.schemas import (
    AnalysisRequest,
    ChangePreview,
    PaginatedResponse,
    PaginationParams,
    PlanDetailResponse,
    PlanResponse,
    SceneChanges,
    SceneFilter,
)
from app.core.dependencies import get_analysis_service, get_db, get_job_service
from app.models import AnalysisPlan, PlanChange, Scene
from app.models.analysis_plan import PlanStatus
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
                "plan_name": request.plan_name
                or f"Analysis - {datetime.now(timezone.utc).isoformat()}",
            },
        )
        # Refresh the job object to ensure all attributes are loaded
        await db.refresh(job)
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
            detect_video_tags=request.options.detect_video_tags,
            confidence_threshold=request.options.confidence_threshold,
        )
        plan = await analysis_service.analyze_scenes(
            scene_ids=scene_ids,
            options=service_options,
            plan_name=request.plan_name
            or f"Analysis - {datetime.now(timezone.utc).isoformat()}",
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
                status=(
                    plan.status.value if hasattr(plan.status, "value") else plan.status  # type: ignore[attr-defined]
                ),
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
        # Refresh the job object to ensure all attributes are loaded
        await db.refresh(job)
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


@router.get("/scenes/{scene_id}/results")
async def get_scene_analysis_results(
    scene_id: str, db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """
    Get all analysis results for a specific scene.

    Returns analysis results from all plans that include this scene.
    """
    # Get all plan changes for this scene
    query = (
        select(PlanChange, AnalysisPlan)
        .join(AnalysisPlan, PlanChange.plan_id == AnalysisPlan.id)
        .where(PlanChange.scene_id == scene_id)
        .order_by(AnalysisPlan.created_at.desc())
    )
    result = await db.execute(query)
    changes_with_plans = result.all()

    # Group changes by plan
    results_by_plan = {}
    for change, plan in changes_with_plans:
        if plan.id not in results_by_plan:
            results_by_plan[plan.id] = {
                "id": plan.id,
                "plan_id": plan.id,
                "scene_id": scene_id,
                "plan": {
                    "id": plan.id,
                    "name": plan.name,
                },
                "model_used": (
                    plan.plan_metadata.get("ai_model", "unknown")
                    if plan.plan_metadata
                    else "unknown"
                ),
                "prompt_used": (
                    plan.plan_metadata.get("prompt_template", "")
                    if plan.plan_metadata
                    else ""
                ),
                "raw_response": (
                    plan.plan_metadata.get("raw_response", "")
                    if plan.plan_metadata
                    else ""
                ),
                "extracted_data": {},
                "confidence_scores": {},
                "processing_time": (
                    plan.plan_metadata.get("processing_time", 0)
                    if plan.plan_metadata
                    else 0
                ),
                "created_at": (
                    plan.created_at.isoformat()
                    if plan.created_at
                    else datetime.now(timezone.utc).isoformat()
                ),
            }

        # Add change data to extracted_data
        field = change.field
        if change.action in ["set", "update"]:
            results_by_plan[plan.id]["extracted_data"][field] = change.proposed_value
        elif change.action == "add" and field in ["performers", "tags"]:
            if field not in results_by_plan[plan.id]["extracted_data"]:
                results_by_plan[plan.id]["extracted_data"][field] = []
            if (
                isinstance(change.proposed_value, dict)
                and "name" in change.proposed_value
            ):
                results_by_plan[plan.id]["extracted_data"][field].append(
                    change.proposed_value["name"]
                )
            else:
                results_by_plan[plan.id]["extracted_data"][field].append(
                    change.proposed_value
                )

        # Add confidence score if available
        if change.confidence is not None:
            results_by_plan[plan.id]["confidence_scores"][field] = change.confidence

    return list(results_by_plan.values())


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


async def _get_plan_change_counts(
    plan_id: int, db: AsyncSession
) -> tuple[int, int, int, int]:
    """Get counts of total, applied, rejected, and pending changes for a plan."""
    # Total changes count
    total_query = select(func.count(PlanChange.id)).where(PlanChange.plan_id == plan_id)
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    if total == 0:
        return 0, 0, 0, 0

    # Applied changes count
    applied_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id, PlanChange.applied.is_(True)
    )
    applied_result = await db.execute(applied_query)
    applied = applied_result.scalar_one()

    # Rejected changes count
    rejected_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id, PlanChange.rejected.is_(True)
    )
    rejected_result = await db.execute(rejected_query)
    rejected = rejected_result.scalar_one()

    # Pending changes count
    pending_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id,
        PlanChange.applied.is_(False),
        PlanChange.rejected.is_(False),
    )
    pending_result = await db.execute(pending_query)
    pending = pending_result.scalar_one()

    return total, applied, rejected, pending


async def _update_plan_status_based_on_counts(
    plan: AnalysisPlan,
    total: int,
    applied: int,
    rejected: int,
    pending: int,
) -> None:
    """Update plan status based on change counts."""
    if total == 0:
        return

    # If any changes have been reviewed (applied or rejected), mark as reviewing
    if (applied > 0 or rejected > 0) and plan.status == PlanStatus.DRAFT:
        plan.status = PlanStatus.REVIEWING  # type: ignore[assignment]

    # If all non-rejected changes are applied, mark as applied
    if applied > 0 and pending == 0 and applied + rejected == total:
        plan.status = PlanStatus.APPLIED  # type: ignore[assignment]
        if not plan.applied_at:
            plan.applied_at = datetime.now(timezone.utc)  # type: ignore[assignment]


def _validate_bulk_action_params(
    action: str, field: Optional[str], confidence_threshold: Optional[float]
) -> None:
    """Validate parameters for bulk actions."""
    if action in ["accept_by_field", "reject_by_field"] and not field:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field parameter is required for field-based actions",
        )

    if action == "accept_by_confidence" and confidence_threshold is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confidence threshold is required for accept_by_confidence action",
        )


def _build_bulk_update_query(
    plan_id: int,
    action: str,
    scene_id: Optional[str],
    field: Optional[str],
    confidence_threshold: Optional[float],
) -> Select[tuple[PlanChange]]:
    """Build query for bulk update based on action and filters."""
    query = select(PlanChange).where(
        PlanChange.plan_id == plan_id,
        PlanChange.applied.is_(False),  # Don't modify already applied changes
    )

    # Add scene filter if provided
    if scene_id:
        query = query.where(PlanChange.scene_id == scene_id)

    # Apply action-specific filters
    if action in ["accept_by_field", "reject_by_field"]:
        query = query.where(PlanChange.field == field)
    elif action == "accept_by_confidence":
        query = query.where(PlanChange.confidence >= confidence_threshold)

    # Only update pending changes
    query = query.where(
        PlanChange.rejected.is_(False),
        PlanChange.applied.is_(False),
    )

    return query


def _apply_bulk_action(changes: Sequence[PlanChange], action: str) -> int:
    """Apply the bulk action to changes and return count of updated items."""
    updated_count = 0
    is_accept_action = action in [
        "accept_all",
        "accept_by_field",
        "accept_by_confidence",
    ]

    for change in changes:
        # Type ignore needed because MyPy doesn't understand SQLAlchemy attribute assignment
        change.applied = False  # type: ignore[assignment]
        change.rejected = not is_accept_action  # type: ignore[assignment]
        updated_count += 1

    return updated_count


@router.post("/plans/{plan_id}/bulk-update")
async def bulk_update_changes(
    plan_id: int,
    action: str = Body(
        ...,
        description="Action to perform: accept_all, reject_all, accept_by_field, reject_by_field, accept_by_confidence",
    ),
    field: Optional[str] = Body(None, description="Field name for field-based actions"),
    confidence_threshold: Optional[float] = Body(
        None, description="Confidence threshold for accept_by_confidence"
    ),
    scene_id: Optional[str] = Body(
        None, description="Optional scene ID to limit changes to a specific scene"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Bulk update change statuses for a plan.

    Actions:
    - accept_all: Accept all pending changes
    - reject_all: Reject all pending changes
    - accept_by_field: Accept all changes for a specific field
    - reject_by_field: Reject all changes for a specific field
    - accept_by_confidence: Accept all changes above a confidence threshold
    """
    # Verify plan exists
    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis plan {plan_id} not found",
        )

    # Validate parameters
    _validate_bulk_action_params(action, field, confidence_threshold)

    # Build and execute query
    query = _build_bulk_update_query(
        plan_id, action, scene_id, field, confidence_threshold
    )
    result = await db.execute(query)
    changes = result.scalars().all()

    # Apply the action
    updated_count = _apply_bulk_action(changes, action)

    # Commit changes
    await db.commit()

    # Update plan status
    total_count, applied_count, rejected_count, pending_count = (
        await _get_plan_change_counts(plan_id, db)
    )
    await _update_plan_status_based_on_counts(
        plan, total_count, applied_count, rejected_count, pending_count
    )

    # If all changes are rejected, mark plan as cancelled
    if total_count > 0 and rejected_count == total_count:
        plan.status = PlanStatus.CANCELLED  # type: ignore[assignment]

    await db.commit()

    return {
        "action": action,
        "updated_count": updated_count,
        "plan_status": (
            plan.status.value if hasattr(plan.status, "value") else plan.status
        ),
        "total_changes": total_count,
        "applied_changes": applied_count,
        "rejected_changes": rejected_count,
        "pending_changes": pending_count,
    }


@router.patch("/plans/{plan_id}/cancel")
async def cancel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Cancel a plan, marking it as cancelled.
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

    # Check if plan can be cancelled
    if plan.status == PlanStatus.APPLIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an already applied plan",
        )

    # Update status
    plan.status = PlanStatus.CANCELLED  # type: ignore[assignment]
    await db.commit()

    return {
        "id": plan.id,
        "status": plan.status.value if hasattr(plan.status, "value") else plan.status,
        "message": "Plan has been cancelled",
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

    # Get change counts and update plan status
    total_count, applied_count, rejected_count, pending_count = (
        await _get_plan_change_counts(cast(int, change.plan_id), db)
    )
    await _update_plan_status_based_on_counts(
        plan, total_count, applied_count, rejected_count, pending_count
    )

    # If all changes are rejected, mark plan as cancelled
    if total_count > 0 and rejected_count == total_count:
        plan.status = PlanStatus.CANCELLED  # type: ignore[assignment]

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
        "plan_status": (
            plan.status.value if hasattr(plan.status, "value") else plan.status
        ),
    }


@router.get("/plans/{plan_id}/costs")
async def get_plan_costs(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get cost breakdown for an analysis plan.

    Returns API usage costs and token statistics.
    """
    # Get plan
    plan = await db.get(AnalysisPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Extract API usage from metadata
    api_usage = plan.get_metadata("api_usage", {})

    if not api_usage:
        return {
            "plan_id": plan_id,
            "total_cost": 0.0,
            "total_tokens": 0,
            "cost_breakdown": {},
            "token_breakdown": {},
            "model": None,
            "currency": "USD",
            "message": "No API usage data available for this plan",
        }

    return {
        "plan_id": plan_id,
        "total_cost": api_usage.get("total_cost", 0.0),
        "total_tokens": api_usage.get("total_tokens", 0),
        "prompt_tokens": api_usage.get("prompt_tokens", 0),
        "completion_tokens": api_usage.get("completion_tokens", 0),
        "cost_breakdown": api_usage.get("cost_breakdown", {}),
        "token_breakdown": api_usage.get("token_breakdown", {}),
        "model": api_usage.get("model"),
        "scenes_analyzed": api_usage.get("scenes_analyzed", 0),
        "average_cost_per_scene": api_usage.get("average_cost_per_scene", 0.0),
        "currency": "USD",
    }


@router.get("/models")
async def get_available_models() -> dict[str, Any]:
    """
    Get available OpenAI models with pricing information.

    Returns models grouped by category with pricing details.
    """
    from app.config.models import (
        DEFAULT_MODEL,
        MODEL_CATEGORIES,
        OPENAI_MODELS,
        RECOMMENDED_MODELS,
    )

    return {
        "models": OPENAI_MODELS,
        "categories": MODEL_CATEGORIES,
        "default": DEFAULT_MODEL,
        "recommended": RECOMMENDED_MODELS,
    }


async def _get_scene_ids_from_filters(
    filters: Optional[SceneFilter],
    db: AsyncSession,
) -> list[str]:
    """Extract scene IDs from filters.

    Args:
        filters: Scene filters
        db: Database session

    Returns:
        List of scene IDs
    """
    if not filters:
        return []

    query = select(Scene.id)
    conditions = []

    if filters.search:
        search_term = f"%{filters.search}%"
        conditions.append(
            or_(Scene.title.ilike(search_term), Scene.details.ilike(search_term))
        )

    if filters.studio_id:
        conditions.append(Scene.studio_id == filters.studio_id)

    if filters.organized is not None:
        conditions.append(Scene.organized == filters.organized)

    if filters.analyzed is not None:
        conditions.append(Scene.analyzed == filters.analyzed)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    return [str(row[0]) for row in result]


@router.post("/video-tags")
async def analyze_video_tags(
    request: AnalysisRequest,
    background: bool = Query(True, description="Run as background job"),
    job_service: JobService = Depends(get_job_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Analyze scenes for tags and markers from video content.

    This endpoint immediately applies detected tags and markers to scenes
    rather than creating a plan. It communicates with an external AI server
    to process video files.

    Args:
        request: Analysis request with scene_ids or filters
        background: Whether to run as background job

    Returns:
        Job info if background, or results if synchronous
    """
    # Validate scene selection
    if not request.scene_ids and not request.filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either scene_ids or filters must be provided",
        )

    # Ensure video tags option is enabled
    if not request.options or not request.options.detect_video_tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="detect_video_tags must be enabled for this endpoint",
        )

    # Get scene IDs
    scene_ids = request.scene_ids
    if not scene_ids and request.filters:
        scene_ids = await _get_scene_ids_from_filters(request.filters, db)

    if not scene_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scenes found matching the criteria",
        )

    if background:
        # Create background job
        job = await job_service.create_job(
            job_type=ModelJobType.VIDEO_TAG_ANALYSIS,
            metadata={
                "scene_ids": scene_ids,
                "filters": request.filters.model_dump() if request.filters else None,
                "description": f"Analyzing video tags for {len(scene_ids)} scenes",
                "job_params": {
                    "scene_ids": scene_ids,
                    "filters": (
                        request.filters.model_dump() if request.filters else None
                    ),
                },
            },
            db=db,
        )

        return {
            "job_id": str(job.id),
            "status": "running",
            "message": f"Analyzing video tags for {len(scene_ids)} scenes",
        }
    else:
        # Run synchronously
        try:
            result = await analysis_service.analyze_and_apply_video_tags(
                scene_ids=scene_ids,
                filters=request.filters.model_dump() if request.filters else None,
            )

            return {
                "status": "completed",
                "result": result,
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video tag analysis failed: {str(e)}",
            )
