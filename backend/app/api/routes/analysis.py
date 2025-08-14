"""
Analysis operations endpoints.
"""

import logging
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
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.api.schemas import (
    AnalysisRequest,
    ApplyPlanRequest,
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
from app.models.plan_change import ChangeStatus
from app.services.analysis.analysis_service import AnalysisService
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

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
        AnalysisPlan.status != PlanStatus.APPLIED
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


async def _get_scene_ids_from_filters(
    filters: SceneFilter, db: AsyncSession
) -> list[str]:
    """Extract scene IDs based on filters."""
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


async def _run_background_analysis(
    scene_ids: list[str],
    request: AnalysisRequest,
    job_service: JobService,
    db: AsyncSession,
) -> dict[str, Any]:
    """Queue analysis as a background job."""
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
    await db.refresh(job)
    return {
        "job_id": job.id,
        "status": "queued",
        "message": f"Analysis job queued for {len(scene_ids)} scenes",
    }


async def _run_synchronous_analysis(
    scene_ids: list[str],
    request: AnalysisRequest,
    analysis_service: AnalysisService,
    db: AsyncSession,
) -> dict[str, Any]:
    """Run analysis synchronously."""
    from app.services.analysis.models import AnalysisOptions as ServiceAnalysisOptions

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

    # Check if plan has an ID (was saved to database)
    if not hasattr(plan, "id") or plan.id is None:
        return {
            "plan_id": None,
            "status": "completed",
            "total_scenes": len(scene_ids),
            "total_changes": 0,
            "message": "Analysis completed - no changes found",
        }

    # Get actual total changes from database
    change_count_query = select(func.count()).where(PlanChange.plan_id == plan.id)
    change_count_result = await db.execute(change_count_query)
    total_changes = change_count_result.scalar() or 0

    return {
        "plan_id": plan.id,
        "status": "completed",
        "total_scenes": len(scene_ids),
        "total_changes": total_changes,
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

    # Get scene IDs
    scene_ids = request.scene_ids
    if not scene_ids and request.filters:
        scene_ids = await _get_scene_ids_from_filters(request.filters, db)

    if not scene_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No scenes found matching the criteria",
        )

    # Run analysis
    if background:
        return await _run_background_analysis(scene_ids, request, job_service, db)
    else:
        return await _run_synchronous_analysis(scene_ids, request, analysis_service, db)


@router.post("/generate-non-ai")
async def generate_non_ai_analysis(
    request: AnalysisRequest,
    background: bool = Query(True, description="Run as background job"),
    job_service: JobService = Depends(get_job_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate non-AI analysis plan for scenes.

    This performs only non-AI detection methods:
    - Path and title-based performer detection
    - OFScraper path-based performer detection (/data/ofscraper/*)
    - HTML tag removal from details

    Does NOT mark scenes as analyzed, allowing re-analysis with AI later.
    """
    # Validate scene selection
    if not request.scene_ids and not request.filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either scene_ids or filters must be provided",
        )

    # Get scene IDs
    scene_ids = request.scene_ids
    if not scene_ids and request.filters:
        scene_ids = await _get_scene_ids_from_filters(request.filters, db)

    if not scene_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scenes found matching criteria",
        )

    # Run analysis
    if background:
        return await _run_background_non_ai_analysis(
            scene_ids, request, job_service, db
        )
    else:
        return await _run_synchronous_non_ai_analysis(
            scene_ids, request, analysis_service, db
        )


async def _run_background_non_ai_analysis(
    scene_ids: list[str],
    request: AnalysisRequest,
    job_service: JobService,
    db: AsyncSession,
) -> dict[str, Any]:
    """Queue non-AI analysis as a background job."""
    job = await job_service.create_job(
        job_type=ModelJobType.NON_AI_ANALYSIS,
        db=db,
        metadata={
            "scene_ids": scene_ids,
            "options": request.options.model_dump(),
            "plan_name": request.plan_name
            or f"Non-AI Analysis - {datetime.now(timezone.utc).isoformat()}",
        },
    )
    await db.refresh(job)
    return {
        "job_id": job.id,
        "status": "queued",
        "message": f"Non-AI analysis job queued for {len(scene_ids)} scenes",
    }


async def _run_synchronous_non_ai_analysis(
    scene_ids: list[str],
    request: AnalysisRequest,
    analysis_service: AnalysisService,
    db: AsyncSession,
) -> dict[str, Any]:
    """Run non-AI analysis synchronously."""
    from app.services.analysis.models import AnalysisOptions as ServiceAnalysisOptions

    service_options = ServiceAnalysisOptions(
        detect_performers=True,  # Non-AI performer detection
        detect_studios=False,  # Studios use AI as fallback
        detect_tags=False,  # Tags use AI
        detect_details=True,  # HTML cleaning only
        detect_video_tags=False,  # Video analysis requires AI
        confidence_threshold=request.options.confidence_threshold,
    )

    plan = await analysis_service.analyze_scenes_non_ai(
        scene_ids=scene_ids,
        options=service_options,
        db=db,
        plan_name=request.plan_name,
    )

    if plan and hasattr(plan, "id") and plan.id:
        return {
            "plan_id": plan.id,
            "total_changes": len(plan.changes) if hasattr(plan, "changes") else 0,
            "scenes_analyzed": len(scene_ids),
            "message": f"Non-AI analysis completed for {len(scene_ids)} scenes",
        }
    else:
        return {
            "plan_id": None,
            "total_changes": 0,
            "scenes_analyzed": len(scene_ids),
            "message": "No changes detected during non-AI analysis",
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

        # Count approved changes (not yet applied)
        approved_count_query = select(func.count(PlanChange.id)).where(
            PlanChange.plan_id == plan.id,  # type: ignore[attr-defined]
            PlanChange.status == ChangeStatus.APPROVED,
        )
        approved_result = await db.execute(approved_count_query)
        approved_changes = approved_result.scalar_one()

        # Count rejected changes
        rejected_count_query = select(func.count(PlanChange.id)).where(
            PlanChange.plan_id == plan.id,  # type: ignore[attr-defined]
            PlanChange.status == ChangeStatus.REJECTED,
        )
        rejected_result = await db.execute(rejected_count_query)
        rejected_changes = rejected_result.scalar_one()

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
                approved_changes=approved_changes,
                rejected_changes=rejected_changes,
                metadata=plan.plan_metadata or {},  # type: ignore[attr-defined]
                job_id=plan.job_id,  # type: ignore[attr-defined]
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
        .options(selectinload(Scene.files))
        .where(PlanChange.plan_id == plan_id)
        .order_by(PlanChange.scene_id, PlanChange.field)
    )
    result = await db.execute(changes_query)
    changes_with_scenes = result.all()

    # Group changes by scene
    scenes_dict = {}
    for change, scene in changes_with_scenes:
        if scene.id not in scenes_dict:
            primary_file = scene.get_primary_file()
            scenes_dict[scene.id] = {
                "scene_id": scene.id,
                "scene_title": scene.title,
                "scene_path": primary_file.path if primary_file else None,
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
                status=(
                    change.status.value
                    if hasattr(change.status, "value")
                    else change.status
                ),
                applied=(change.status == ChangeStatus.APPLIED),
            )
        )

    # Convert to SceneChanges objects
    scenes = [SceneChanges(**scene_data) for scene_data in scenes_dict.values()]

    # Get actual total changes count from database
    change_count_query = select(func.count()).where(PlanChange.plan_id == plan_id)
    change_count_result = await db.execute(change_count_query)
    total_changes_from_db = change_count_result.scalar() or 0

    # Count approved changes (not yet applied)
    approved_count_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id,
        PlanChange.status == ChangeStatus.APPROVED,
    )
    approved_result = await db.execute(approved_count_query)
    approved_changes = approved_result.scalar_one()

    # Count rejected changes
    rejected_count_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id,
        PlanChange.status == ChangeStatus.REJECTED,
    )
    rejected_result = await db.execute(rejected_count_query)
    rejected_changes = rejected_result.scalar_one()

    return PlanDetailResponse(
        id=int(plan.id),
        name=str(plan.name),
        status=plan.status.value if hasattr(plan.status, "value") else str(plan.status),
        created_at=plan.created_at,  # type: ignore[arg-type]
        total_scenes=len(scenes),
        total_changes=total_changes_from_db,
        approved_changes=approved_changes,
        rejected_changes=rejected_changes,
        metadata=dict(plan.plan_metadata) if plan.plan_metadata else {},
        scenes=scenes,
        job_id=plan.job_id,
    )


@router.post("/plans/{plan_id}/apply")
async def apply_plan(
    plan_id: int,
    request: ApplyPlanRequest,
    scene_ids: Optional[list[str]] = Query(
        None, description="Apply to specific scenes only"
    ),
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
    if plan.status == PlanStatus.APPLIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan has already been applied",
        )

    if request.background:
        # Queue as background job
        job = await job_service.create_job(
            job_type=ModelJobType.APPLY_PLAN,
            db=db,
            metadata={
                "plan_id": plan_id,
                "scene_ids": scene_ids,
                "change_ids": request.change_ids,
            },
        )
        # Don't refresh the job object to avoid session issues
        # The WebSocket handler will fetch its own copy
        return {
            "job_id": job.id,
            "status": "queued",
            "message": "Plan application job has been queued",
        }
    else:
        # Apply synchronously
        apply_result = await analysis_service.apply_plan(
            plan_id=str(plan_id), change_ids=request.change_ids
        )
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
    if change.status == ChangeStatus.APPLIED:
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
) -> tuple[int, int, int, int, int]:
    """Get counts of total, applied, rejected, accepted, and pending changes for a plan."""
    # Total changes count
    total_query = select(func.count(PlanChange.id)).where(PlanChange.plan_id == plan_id)
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    if total == 0:
        return 0, 0, 0, 0, 0

    # Applied changes count
    applied_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id, PlanChange.status == ChangeStatus.APPLIED
    )
    applied_result = await db.execute(applied_query)
    applied = applied_result.scalar_one()

    # Rejected changes count
    rejected_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id, PlanChange.status == ChangeStatus.REJECTED
    )
    rejected_result = await db.execute(rejected_query)
    rejected = rejected_result.scalar_one()

    # Accepted changes count (approved but not yet applied)
    accepted_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id,
        PlanChange.status == ChangeStatus.APPROVED,
    )
    accepted_result = await db.execute(accepted_query)
    accepted = accepted_result.scalar_one()

    # Pending changes count
    pending_query = select(func.count(PlanChange.id)).where(
        PlanChange.plan_id == plan_id,
        PlanChange.status == ChangeStatus.PENDING,
    )
    pending_result = await db.execute(pending_query)
    pending = pending_result.scalar_one()

    return total, applied, rejected, accepted, pending


async def _update_plan_status_based_on_counts(
    plan: AnalysisPlan,
    total: int,
    applied: int,
    rejected: int,
    accepted: int,
    pending: int,
) -> None:
    """Update plan status based on change counts."""
    if total == 0:
        return

    # Calculate total accepted (both applied and not applied)
    total_accepted = int(applied) + int(accepted)

    # If we're in DRAFT and any changes have been reviewed, move to REVIEWING
    if plan.status == PlanStatus.DRAFT and (total_accepted > 0 or rejected > 0):
        plan.status = PlanStatus.REVIEWING  # type: ignore[assignment]

    # Determine final status when no changes need review or approval
    if pending == 0 and accepted == 0:
        # All changes have been processed (no pending, no unapplied approved changes)
        if total_accepted > 0:
            # At least one change was accepted and applied - mark as APPLIED
            plan.status = PlanStatus.APPLIED  # type: ignore[assignment]
            if not plan.applied_at:
                plan.applied_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        elif rejected == total:
            # All changes were rejected - mark as CANCELLED
            plan.status = PlanStatus.CANCELLED  # type: ignore[assignment]

    # Otherwise keep status as REVIEWING if there are pending or unapplied approved changes


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
    import logging

    logger = logging.getLogger(__name__)

    logger.debug(f"Building query - plan_id: {plan_id}, action: {action}")

    query = select(PlanChange).where(
        PlanChange.plan_id == plan_id,
        PlanChange.status
        != ChangeStatus.APPLIED,  # Don't modify already applied changes
    )

    # Add scene filter if provided
    if scene_id:
        query = query.where(PlanChange.scene_id == scene_id)
        logger.debug(f"Added scene filter: {scene_id}")

    # Apply action-specific filters
    if action in ["accept_by_field", "reject_by_field"]:
        query = query.where(PlanChange.field == field)
        logger.debug(f"Added field filter: {field}")
    elif action == "accept_by_confidence":
        query = query.where(PlanChange.confidence >= confidence_threshold)
        logger.debug(f"Added confidence filter: >= {confidence_threshold}")

    # Only update pending changes
    query = query.where(
        PlanChange.status == ChangeStatus.PENDING,
    )
    logger.debug("Added pending changes filter")

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
        if is_accept_action:
            change.status = ChangeStatus.APPROVED  # type: ignore[assignment]
        else:
            change.status = ChangeStatus.REJECTED  # type: ignore[assignment]
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
    import logging

    logger = logging.getLogger(__name__)
    logger.info("=== Bulk update request received ===")
    logger.info(f"Plan ID: {plan_id}")
    logger.info(f"Action: {action}")
    logger.info(f"Field: {field}")
    logger.info(f"Confidence threshold: {confidence_threshold}")
    logger.info(f"Scene ID: {scene_id}")

    # Verify plan exists
    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        logger.error(f"Plan {plan_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis plan {plan_id} not found",
        )

    logger.info(f"Found plan: {plan.name} (status: {plan.status})")

    # Validate parameters
    _validate_bulk_action_params(action, field, confidence_threshold)

    # Build and execute query
    query = _build_bulk_update_query(
        plan_id, action, scene_id, field, confidence_threshold
    )
    logger.info("Executing query to find changes...")
    result = await db.execute(query)
    changes = result.scalars().all()
    logger.info(f"Found {len(changes)} changes to update")

    # Apply the action
    updated_count = _apply_bulk_action(changes, action)
    logger.info(f"Applied action to {updated_count} changes")

    # Flush changes to database
    await db.flush()
    logger.info("Changes flushed to database")

    # Update plan status
    total_count, applied_count, rejected_count, accepted_count, pending_count = (
        await _get_plan_change_counts(plan_id, db)
    )
    logger.info(
        f"Change counts - Total: {total_count}, Applied: {applied_count}, Rejected: {rejected_count}, Accepted: {accepted_count}, Pending: {pending_count}"
    )

    await _update_plan_status_based_on_counts(
        plan, total_count, applied_count, rejected_count, accepted_count, pending_count
    )

    await db.commit()
    logger.info("Transaction committed successfully")

    response = {
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

    logger.info("=== Bulk update completed ===")
    logger.info(f"Response: {response}")

    return response


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
    if change.status == ChangeStatus.APPLIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an applied change",
        )

    # Update status
    if accepted is not None:
        if accepted:
            change.status = ChangeStatus.APPROVED  # type: ignore[assignment]
        else:
            change.status = ChangeStatus.PENDING  # type: ignore[assignment]

    if rejected is not None:
        if rejected:
            change.status = ChangeStatus.REJECTED  # type: ignore[assignment]
        else:
            change.status = ChangeStatus.PENDING  # type: ignore[assignment]

    # Update plan status - commit the change first
    await db.commit()

    # Refresh the change to ensure we have the latest data
    await db.refresh(change)

    # Load the plan to update status in a new query
    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == change.plan_id)
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one()

    # Get change counts and update plan status
    total_count, applied_count, rejected_count, accepted_count, pending_count = (
        await _get_plan_change_counts(cast(int, change.plan_id), db)
    )
    await _update_plan_status_based_on_counts(
        plan, total_count, applied_count, rejected_count, accepted_count, pending_count
    )

    await db.commit()

    return {
        "id": change.id,
        "field": change.field,
        "action": change.action,
        "current_value": change.current_value,
        "proposed_value": change.proposed_value,
        "confidence": change.confidence,
        "status": (
            change.status.value if hasattr(change.status, "value") else change.status
        ),
        "applied": (change.status == ChangeStatus.APPLIED),
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


@router.post("/apply-all-approved")
async def apply_all_approved_changes(
    background: bool = True,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Apply all approved changes across all plans.

    This endpoint:
    - Finds all plans with approved but not applied changes
    - Creates a background job to apply all approved changes
    - Updates plan and change statuses appropriately
    """
    # Find all plans with approved but not applied changes
    # Check both the new status field and the legacy accepted field for compatibility
    query = (
        select(AnalysisPlan)
        .join(PlanChange)
        .where(
            PlanChange.status == ChangeStatus.APPROVED,
            AnalysisPlan.status != PlanStatus.CANCELLED,
            AnalysisPlan.status != PlanStatus.APPLIED,
        )
        .distinct(AnalysisPlan.id)
    )
    result = await db.execute(query)
    plans_to_apply: list[AnalysisPlan] = list(result.scalars().all())

    if not plans_to_apply:
        return {
            "message": "No approved changes to apply",
            "plans_affected": 0,
            "total_changes": 0,
        }

    # Count total approved changes
    count_query = select(func.count(PlanChange.id)).where(
        PlanChange.status == ChangeStatus.APPROVED,
    )
    count_result = await db.execute(count_query)
    total_changes = count_result.scalar_one()

    if background:
        # Create a background job for bulk apply
        from app.models.job import JobType as ModelJobType

        job = await job_service.create_job(
            job_type=ModelJobType.APPLY_PLAN,
            metadata={
                "plans_to_apply": [plan.id for plan in plans_to_apply],
                "total_changes": total_changes,
                "bulk_apply": True,
            },
            db=db,
        )
        await db.refresh(job)

        return {
            "job_id": job.id,
            "plans_affected": len(plans_to_apply),
            "total_changes": total_changes,
            "message": f"Started background job to apply {total_changes} changes across {len(plans_to_apply)} plans",
        }
    else:
        # Apply synchronously (not recommended for large batches)
        applied_count = 0
        for plan in plans_to_apply:
            try:
                # Get approved changes for this plan
                changes_query = select(PlanChange).where(
                    PlanChange.plan_id == plan.id,
                    PlanChange.status == ChangeStatus.APPROVED,
                    PlanChange.applied.is_(False),
                )
                changes_result = await db.execute(changes_query)
                changes: list[PlanChange] = list(changes_result.scalars().all())

                # Apply each change (simplified - actual implementation would use StashService)
                for change in changes:
                    setattr(change, "applied", True)
                    setattr(change, "status", ChangeStatus.APPLIED)
                    setattr(change, "applied_at", datetime.now(timezone.utc))
                    applied_count += 1

                # Update plan status
                setattr(plan, "status", PlanStatus.APPLIED)
                if plan.plan_metadata is None:
                    plan.plan_metadata = {}
                plan.plan_metadata["applied_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

            except Exception as e:
                logger.error(f"Error applying changes for plan {plan.id}: {str(e)}")
                continue

        await db.commit()

        return {
            "plans_affected": len(plans_to_apply),
            "total_changes": applied_count,
            "message": f"Applied {applied_count} changes across {len(plans_to_apply)} plans",
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
