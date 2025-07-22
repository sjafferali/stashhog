"""
Test endpoints for verifying API functionality.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models import AnalysisPlan, PlanChange

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/bulk-update-test/{plan_id}")
async def test_bulk_update_get(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Test endpoint to verify bulk update data retrieval.

    This endpoint helps debug the bulk update API by:
    1. Checking if the plan exists
    2. Retrieving all changes for the plan
    3. Showing current status of changes
    """
    logger.info(f"Test endpoint called for plan_id: {plan_id}")

    # Check if plan exists
    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        logger.warning(f"Plan {plan_id} not found in test endpoint")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis plan {plan_id} not found",
        )

    logger.info(f"Found plan: {plan.name} (status: {plan.status})")

    # Get all changes for this plan
    changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
    changes_result = await db.execute(changes_query)
    changes = changes_result.scalars().all()

    logger.info(f"Found {len(changes)} total changes for plan {plan_id}")

    # Count changes by status
    pending_changes = [
        c for c in changes if not c.accepted and not c.rejected and not c.applied
    ]
    accepted_changes = [c for c in changes if c.accepted and not c.applied]
    rejected_changes = [c for c in changes if c.rejected]
    applied_changes = [c for c in changes if c.applied]

    # Get unique fields
    unique_fields = list(set(c.field for c in changes))

    # Get changes by field
    changes_by_field = {}
    for field in unique_fields:
        field_changes = [c for c in changes if c.field == field]
        changes_by_field[field] = {
            "total": len(field_changes),
            "pending": len(
                [
                    c
                    for c in field_changes
                    if not c.accepted and not c.rejected and not c.applied
                ]
            ),
            "accepted": len([c for c in field_changes if c.accepted and not c.applied]),
            "rejected": len([c for c in field_changes if c.rejected]),
            "applied": len([c for c in field_changes if c.applied]),
        }

    return {
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "status": (
                plan.status.value if hasattr(plan.status, "value") else plan.status
            ),
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        },
        "summary": {
            "total_changes": len(changes),
            "pending_changes": len(pending_changes),
            "accepted_changes": len(accepted_changes),
            "rejected_changes": len(rejected_changes),
            "applied_changes": len(applied_changes),
        },
        "fields": unique_fields,
        "changes_by_field": changes_by_field,
        "sample_changes": [
            {
                "id": c.id,
                "scene_id": c.scene_id,
                "field": c.field,
                "action": c.action,
                "current_value": c.current_value,
                "proposed_value": c.proposed_value,
                "confidence": c.confidence,
                "accepted": c.accepted,
                "rejected": c.rejected,
                "applied": c.applied,
            }
            for c in changes[:5]  # Show first 5 changes as samples
        ],
    }


def _build_bulk_update_query(
    plan_id: int,
    action: str,
    scene_id: Optional[str],
    field: Optional[str],
    confidence_threshold: Optional[float],
) -> Any:
    """Build query for bulk update based on action and filters."""
    query = select(PlanChange).where(
        PlanChange.plan_id == plan_id,
        PlanChange.applied.is_(False),
        PlanChange.accepted.is_(False),
        PlanChange.rejected.is_(False),
    )

    if scene_id:
        query = query.where(PlanChange.scene_id == scene_id)
        logger.info(f"Filtering by scene_id: {scene_id}")

    if action in ["accept_by_field", "reject_by_field"]:
        if not field:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Field parameter is required for field-based actions",
            )
        query = query.where(PlanChange.field == field)
        logger.info(f"Filtering by field: {field}")

    elif action == "accept_by_confidence":
        if confidence_threshold is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confidence threshold is required for accept_by_confidence action",
            )
        query = query.where(PlanChange.confidence >= confidence_threshold)
        logger.info(f"Filtering by confidence >= {confidence_threshold}")

    return query


def _group_changes_by_field(affected_changes: list) -> dict[str, list[dict[str, Any]]]:
    """Group affected changes by field for analysis."""
    affected_by_field: dict[str, list[dict[str, Any]]] = {}
    for change in affected_changes:
        if change.field not in affected_by_field:
            affected_by_field[change.field] = []
        affected_by_field[change.field].append(
            {
                "id": change.id,
                "scene_id": change.scene_id,
                "current_value": change.current_value,
                "proposed_value": change.proposed_value,
                "confidence": change.confidence,
            }
        )
    return affected_by_field


@router.post("/bulk-update-test/{plan_id}")
async def test_bulk_update_post(
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
    dry_run: bool = Body(
        True, description="If true, only simulate the operation without making changes"
    ),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Test endpoint for bulk update operation with dry-run capability.

    This simulates the bulk update without actually modifying the database.
    """
    logger.info(
        f"Test bulk update called - plan_id: {plan_id}, action: {action}, dry_run: {dry_run}"
    )

    # Verify plan exists
    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        logger.warning(f"Plan {plan_id} not found in test bulk update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis plan {plan_id} not found",
        )

    # Build query for changes that would be affected
    query = _build_bulk_update_query(
        plan_id, action, scene_id, field, confidence_threshold
    )

    # Execute query to get affected changes
    result = await db.execute(query)
    affected_changes = result.scalars().all()

    logger.info(f"Would affect {len(affected_changes)} changes")

    # Group affected changes by field for analysis
    affected_by_field = _group_changes_by_field(affected_changes)

    response = {
        "dry_run": dry_run,
        "action": action,
        "filters": {
            "field": field,
            "confidence_threshold": confidence_threshold,
            "scene_id": scene_id,
        },
        "would_affect": {
            "total_changes": len(affected_changes),
            "changes_by_field": {
                field: len(changes) for field, changes in affected_by_field.items()
            },
        },
        "sample_affected_changes": [
            {
                "id": c.id,
                "scene_id": c.scene_id,
                "field": c.field,
                "current_value": c.current_value,
                "proposed_value": c.proposed_value,
                "confidence": c.confidence,
            }
            for c in affected_changes[:10]  # Show first 10 as samples
        ],
    }

    if not dry_run:
        # Actually perform the update
        is_accept_action = action in [
            "accept_all",
            "accept_by_field",
            "accept_by_confidence",
        ]

        for change in affected_changes:
            if is_accept_action:
                change.accepted = True
                change.rejected = False
            else:
                change.accepted = False
                change.rejected = True

        await db.commit()

        response["message"] = f"Successfully updated {len(affected_changes)} changes"
        logger.info(f"Updated {len(affected_changes)} changes with action: {action}")
    else:
        response["message"] = "Dry run completed - no changes made"

    return response
