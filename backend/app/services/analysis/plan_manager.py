"""Plan management for analysis operations."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.plan_change import ChangeAction, PlanChange
from app.models.scene import Scene
from app.services.stash_service import StashService

from .models import ApplyResult, SceneChanges

logger = logging.getLogger(__name__)


class PlanManager:
    """Manage analysis plans and their execution."""

    def __init__(self) -> None:
        """Initialize plan manager."""
        pass

    async def create_plan(
        self,
        name: str,
        changes: List[SceneChanges],
        metadata: Dict[str, Any],
        db: AsyncSession,
    ) -> AnalysisPlan:
        """Create and save a new analysis plan.

        Args:
            name: Plan name
            changes: List of scene changes
            metadata: Plan metadata (settings, statistics)
            db: Database session

        Returns:
            Created analysis plan
        """
        # Create the plan
        plan = AnalysisPlan(
            name=name,
            description=metadata.get("description", ""),
            plan_metadata=metadata,
            status=PlanStatus.DRAFT,
        )

        db.add(plan)
        await db.flush()  # Get the plan ID

        # Create individual change records and collect scene IDs
        change_count = 0
        analyzed_scene_ids = set()
        for scene_changes in changes:
            analyzed_scene_ids.add(scene_changes.scene_id)
            if scene_changes.has_changes():
                for change in scene_changes.changes:
                    plan_change = PlanChange(
                        plan_id=plan.id,
                        scene_id=scene_changes.scene_id,
                        field=change.field,
                        action=self._map_action(change.action),
                        current_value=self._serialize_value(change.current_value),
                        proposed_value=self._serialize_value(change.proposed_value),
                        confidence=change.confidence,
                    )
                    db.add(plan_change)
                    change_count += 1

        # Mark all analyzed scenes as analyzed=True
        if analyzed_scene_ids:
            await db.execute(
                update(Scene)
                .where(Scene.id.in_(analyzed_scene_ids))
                .values(analyzed=True)
            )
            await db.flush()

        # Update metadata with statistics
        plan.add_metadata("total_changes", change_count)
        plan.add_metadata("scene_count", len(changes))
        plan.add_metadata("created_at", datetime.utcnow().isoformat())

        await db.flush()

        # Refresh the plan
        query = select(AnalysisPlan).where(AnalysisPlan.id == plan.id)
        result = await db.execute(query)
        plan = result.scalar_one()

        logger.info(f"Created analysis plan '{name}' with {change_count} changes")
        return plan

    async def get_plan(self, plan_id: int, db: AsyncSession) -> Optional[AnalysisPlan]:
        """Retrieve a plan with its changes.

        Args:
            plan_id: Plan ID
            db: Database session

        Returns:
            Analysis plan or None
        """
        query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_plans(
        self,
        db: AsyncSession,
        status: Optional[PlanStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AnalysisPlan]:
        """List analysis plans.

        Args:
            db: Database session
            status: Filter by status
            limit: Maximum results
            offset: Skip results

        Returns:
            List of plans
        """
        query = select(AnalysisPlan)

        if status:
            query = query.where(
                AnalysisPlan.status
                == (status.value if hasattr(status, "value") else status)
            )

        query = query.order_by(AnalysisPlan.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def apply_plan(
        self,
        plan_id: int,
        db: AsyncSession,
        stash_service: StashService,
        apply_filters: Optional[Dict[str, bool]] = None,
        change_ids: Optional[List[int]] = None,
    ) -> ApplyResult:
        """Apply changes from a plan to Stash.

        Args:
            plan_id: Plan to apply
            db: Database session
            stash_service: Stash service for applying changes
            apply_filters: Optional filters for what to apply
            change_ids: Optional list of specific change IDs to apply

        Returns:
            Result of applying the plan
        """
        # Validate plan
        plan = await self._validate_plan_for_apply(plan_id, db)

        # Setup filters
        if apply_filters is None:
            apply_filters = self._get_default_apply_filters()

        # Update plan status to reviewing
        await self._update_plan_status_to_reviewing(plan, db)

        # Get changes and apply them
        changes = await self._get_plan_changes(plan_id, db)
        result_data = await self._process_plan_changes(
            changes, apply_filters, db, stash_service, change_ids
        )

        # Finalize plan application
        await self._finalize_plan_application(plan, result_data, db)

        return ApplyResult(
            plan_id=plan_id,
            total_changes=result_data["total_changes"],
            applied_changes=result_data["applied_changes"],
            failed_changes=result_data["failed_changes"],
            errors=result_data["errors"],
        )

    async def _validate_plan_for_apply(
        self, plan_id: int, db: AsyncSession
    ) -> AnalysisPlan:
        """Validate that a plan exists and can be applied."""
        plan = await self.get_plan(plan_id, db)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if not plan.can_be_applied():
            raise ValueError(
                f"Plan {plan_id} cannot be applied (status: {plan.status})"
            )

        return plan

    def _get_default_apply_filters(self) -> Dict[str, bool]:
        """Get default apply filters."""
        return {
            "performers": True,
            "studios": True,
            "tags": True,
            "details": True,
        }

    async def _update_plan_status_to_reviewing(
        self, plan: AnalysisPlan, db: AsyncSession
    ) -> None:
        """Update plan status to reviewing."""
        plan.status = PlanStatus.REVIEWING  # type: ignore[assignment]
        await db.flush()

    async def _get_plan_changes(
        self, plan_id: int, db: AsyncSession
    ) -> List[PlanChange]:
        """Get all changes for a plan."""
        changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
        result = await db.execute(changes_query)
        return list(result.scalars().all())

    async def _process_plan_changes(
        self,
        changes: List[PlanChange],
        apply_filters: Dict[str, bool],
        db: AsyncSession,
        stash_service: StashService,
        change_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Process all changes in a plan."""
        total_changes = 0
        applied_changes = 0
        failed_changes = 0
        errors = []

        for change in changes:
            # Skip filtered, rejected, or already applied changes
            if not self._should_apply_change(change, apply_filters, change_ids):
                continue

            total_changes += 1

            try:
                success = await self.apply_single_change(change, db, stash_service)
                if success:
                    applied_changes += 1
                else:
                    failed_changes += 1
            except Exception as e:
                failed_changes += 1
                errors.append(self._create_error_record(change, e))
                logger.error(f"Failed to apply change {change.id}: {e}")

        return {
            "total_changes": total_changes,
            "applied_changes": applied_changes,
            "failed_changes": failed_changes,
            "errors": errors,
        }

    def _should_apply_change(
        self,
        change: PlanChange,
        apply_filters: Dict[str, bool],
        change_ids: Optional[List[int]] = None,
    ) -> bool:
        """Check if a change should be applied."""
        # If specific change_ids are provided, only apply those
        if change_ids is not None:
            if change.id not in change_ids:
                return False
        else:
            # If no change_ids provided, only apply explicitly accepted changes
            if not change.accepted:
                return False

        if not apply_filters.get(str(change.field), True):
            return False
        if change.rejected:
            return False
        if change.applied:
            return False
        return True

    def _create_error_record(
        self, change: PlanChange, error: Exception
    ) -> Dict[str, Any]:
        """Create an error record for a failed change."""
        return {
            "change_id": change.id,
            "scene_id": change.scene_id,
            "field": change.field,
            "error": str(error),
        }

    async def _finalize_plan_application(
        self, plan: AnalysisPlan, result_data: Dict[str, Any], db: AsyncSession
    ) -> None:
        """Finalize plan application with status and metadata updates."""
        plan.status = PlanStatus.APPLIED  # type: ignore[assignment]
        plan.applied_at = datetime.utcnow()  # type: ignore[assignment]
        plan.add_metadata(
            "apply_result",
            {
                "total": result_data["total_changes"],
                "applied": result_data["applied_changes"],
                "failed": result_data["failed_changes"],
                "errors": len(result_data["errors"]),
            },
        )
        await db.flush()

    async def apply_single_change(
        self, change: PlanChange, db: AsyncSession, stash_service: StashService
    ) -> bool:
        """Apply a single change to Stash.

        Args:
            change: Change to apply
            db: Database session
            stash_service: Stash service

        Returns:
            True if successful
        """
        try:
            scene_id = change.scene_id

            # Get current scene data
            scene = await stash_service.get_scene(str(change.scene_id))
            if not scene:
                logger.error(f"Scene {scene_id} not found")
                return False

            # Prepare update data based on field and action
            update_data = await self._prepare_update_data(change, scene, stash_service)

            # Apply the update
            if update_data:
                await stash_service.update_scene(str(change.scene_id), update_data)

                # Mark change as applied
                change.applied = True  # type: ignore[assignment]
                change.applied_at = datetime.utcnow()  # type: ignore[assignment]
                await db.flush()

                return True
            else:
                logger.warning(f"No update data for change {change.id}")
                return False

        except Exception as e:
            logger.error(f"Error applying change {change.id}: {e}")
            raise  # Re-raise to be caught by the outer exception handler

    async def _prepare_update_data(
        self, change: PlanChange, scene: Dict, stash_service: StashService
    ) -> Dict[str, Any]:
        """Prepare update data for a change."""
        if change.field == "studio":
            return await self._prepare_studio_update(change, stash_service)
        elif change.field == "performers":
            return await self._prepare_performers_update(change, scene, stash_service)
        elif change.field == "tags":
            return await self._prepare_tags_update(change, scene, stash_service)
        elif change.field == "details":
            return self._prepare_details_update(change)
        elif change.field == "title":
            return {"title": change.proposed_value}
        elif change.field == "rating":
            return {"rating": change.proposed_value}
        elif change.field == "markers":
            return await self._prepare_markers_update(change, scene, stash_service)
        else:
            return {}

    async def _prepare_studio_update(
        self, change: PlanChange, stash_service: StashService
    ) -> Dict[str, Any]:
        """Prepare studio update data."""
        if change.action != ChangeAction.SET:
            return {}

        studio_name = change.proposed_value
        if isinstance(studio_name, dict):
            studio_name = studio_name.get("name", "")

        if studio_name:
            # Try to find existing studio first
            studio = await stash_service.find_studio(str(studio_name))
            if not studio:
                # Create new studio
                studio = await stash_service.create_studio(str(studio_name))
            if studio:
                return {"studio_id": studio["id"]}
        return {}

    async def _prepare_performers_update(
        self, change: PlanChange, scene: Dict, stash_service: StashService
    ) -> Dict[str, Any]:
        """Prepare performers update data."""
        current_ids = [p["id"] for p in scene.get("performers", [])]

        if change.action == (
            ChangeAction.ADD.value
            if hasattr(ChangeAction.ADD, "value")
            else ChangeAction.ADD
        ):
            new_ids = await self._add_performers(
                change.proposed_value, current_ids, stash_service
            )
            return {"performer_ids": new_ids}
        elif change.action == (
            ChangeAction.REMOVE.value
            if hasattr(ChangeAction.REMOVE, "value")
            else ChangeAction.REMOVE
        ):
            remaining_ids = self._remove_performers(
                change.proposed_value, current_ids, scene.get("performers", [])
            )
            return {"performer_ids": remaining_ids}
        return {}

    async def _add_performers(
        self, new_performers: Any, current_ids: List[str], stash_service: StashService
    ) -> List[str]:
        """Add new performers to current list."""
        if not isinstance(new_performers, list):
            new_performers = [new_performers]

        result_ids = current_ids.copy()
        for performer_name in new_performers:
            if isinstance(performer_name, dict):
                performer_name = performer_name.get("name", "")

            if performer_name:
                # Try to find existing performer first
                performer = await stash_service.find_performer(performer_name)
                if not performer:
                    # Create new performer
                    performer = await stash_service.create_performer(performer_name)
                if performer and performer["id"] not in result_ids:
                    result_ids.append(performer["id"])

        return result_ids

    def _remove_performers(
        self, remove_names: Any, current_ids: List[str], current_performers: List[Dict]
    ) -> List[str]:
        """Remove performers from current list."""
        if not isinstance(remove_names, list):
            remove_names = [remove_names]

        # Get IDs to remove
        remove_ids = []
        for name in remove_names:
            if isinstance(name, dict):
                name = name.get("name", "")
            for p in current_performers:
                if p.get("name", "").lower() == name.lower():
                    remove_ids.append(p["id"])

        return [pid for pid in current_ids if pid not in remove_ids]

    async def _prepare_tags_update(
        self, change: PlanChange, scene: Dict, stash_service: StashService
    ) -> Dict[str, Any]:
        """Prepare tags update data."""
        current_ids = [t["id"] for t in scene.get("tags", [])]

        if change.action == (
            ChangeAction.ADD.value
            if hasattr(ChangeAction.ADD, "value")
            else ChangeAction.ADD
        ):
            new_ids = await self._add_tags(
                change.proposed_value, current_ids, stash_service
            )
            return {"tag_ids": new_ids}
        return {}

    async def _add_tags(
        self, new_tags: Any, current_ids: List[str], stash_service: StashService
    ) -> List[str]:
        """Add new tags to current list."""
        if not isinstance(new_tags, list):
            new_tags = [new_tags]

        result_ids = current_ids.copy()
        for tag_name in new_tags:
            if isinstance(tag_name, dict):
                tag_name = tag_name.get("name", "")

            if tag_name:
                # Try to find existing tag first
                tag = await stash_service.find_tag(tag_name)
                if not tag:
                    # Create new tag
                    tag = await stash_service.create_tag(tag_name)
                if tag and tag["id"] not in result_ids:
                    result_ids.append(tag["id"])

        return result_ids

    def _prepare_details_update(self, change: PlanChange) -> Dict[str, Any]:
        """Prepare details update data."""
        if change.action in [ChangeAction.UPDATE, ChangeAction.SET, ChangeAction.ADD]:
            details = change.proposed_value
            if isinstance(details, dict):
                details = details.get("text", "")
            return {"details": details}
        return {}

    async def _prepare_markers_update(
        self, change: PlanChange, scene: Dict, stash_service: StashService
    ) -> Dict[str, Any]:
        """Prepare markers update data.

        Note: Markers are handled differently - they need to be created individually
        rather than updated on the scene.
        """
        if change.action == ChangeAction.ADD:
            # Markers are added through separate create_marker calls
            # They're not part of the scene update payload
            markers_value = change.proposed_value
            if not isinstance(markers_value, list):
                markers_to_create = [markers_value]
            else:
                markers_to_create = markers_value

            for marker_data in markers_to_create:
                # Ensure scene_id is set correctly
                marker_data["scene_id"] = scene["id"]

                # Convert tag names to tag IDs
                marker_tags = []
                for tag_name in marker_data.get("tags", []):
                    # Get database session
                    from app.core.database import AsyncSessionLocal

                    async with AsyncSessionLocal() as db:
                        tag_id = await stash_service.find_or_create_tag(tag_name, db)
                        if tag_id:
                            marker_tags.append(tag_id)

                # Only create marker if we have at least one tag
                if not marker_tags:
                    logger.warning(
                        f"Skipping marker creation - no tags found for marker at {marker_data.get('seconds', 0)}s"
                    )
                    continue

                # Create marker with proper format
                marker_to_create = {
                    "scene_id": scene["id"],
                    "seconds": marker_data.get("seconds", 0),
                    "title": marker_data.get("title", ""),
                    "tag_ids": marker_tags,
                }

                # Add end_seconds if provided
                if "end_seconds" in marker_data:
                    marker_to_create["end_seconds"] = marker_data["end_seconds"]

                try:
                    await stash_service.create_marker(marker_to_create)  # type: ignore[arg-type]
                    logger.info(
                        f"Created marker for scene {scene['id']} at {marker_data.get('seconds', 0)}s"
                    )
                except Exception as e:
                    logger.error(f"Failed to create marker: {e}")
                    raise

            # Return empty dict as markers are handled separately
            return {}

        # Other actions not supported for markers yet
        return {}

    async def delete_plan(self, plan_id: int, db: AsyncSession) -> bool:
        """Delete an analysis plan.

        Args:
            plan_id: Plan to delete
            db: Database session

        Returns:
            True if deleted
        """
        plan = await self.get_plan(plan_id, db)
        if not plan:
            return False

        if plan.status == (
            PlanStatus.APPLIED.value
            if hasattr(PlanStatus.APPLIED, "value")
            else PlanStatus.APPLIED
        ):
            raise ValueError("Cannot delete an applied plan")

        await db.delete(plan)
        await db.flush()

        logger.info(f"Deleted plan {plan_id}")
        return True

    def _map_action(self, action: str) -> ChangeAction:
        """Map string action to enum.

        Args:
            action: Action string

        Returns:
            ChangeAction enum
        """
        action_map = {
            "add": ChangeAction.ADD,
            "remove": ChangeAction.REMOVE,
            "update": ChangeAction.UPDATE,
            "set": ChangeAction.SET,
        }
        return action_map.get(action.lower(), ChangeAction.UPDATE)

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for database storage.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (list, dict)):
            return value
        else:
            # Convert to string for unknown types
            return str(value)

    async def update_plan_status(
        self, plan_id: int, status: PlanStatus, db: AsyncSession
    ) -> None:
        """Update the status of a plan.

        Args:
            plan_id: Plan ID
            status: New status
            db: Database session
        """
        plan = await self.get_plan(plan_id, db)
        if plan:
            plan.status = status  # type: ignore[assignment]
            await db.flush()

    async def get_plan_statistics(
        self, plan_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        """Get statistics for a plan.

        Args:
            plan_id: Plan ID
            db: Database session

        Returns:
            Dictionary of statistics
        """
        plan = await self.get_plan(plan_id, db)
        if not plan:
            return {}

        # Get all changes for the plan
        query = select(PlanChange).where(PlanChange.plan_id == plan_id)
        result = await db.execute(query)
        changes = result.scalars().all()

        # Calculate statistics
        total_changes = len(changes)
        scenes_affected = len(set(c.scene_id for c in changes))

        # Count by action
        changes_by_action: Dict[str, int] = {}
        for change in changes:
            action_str = (
                change.action.value
                if hasattr(change.action, "value")
                else str(change.action)
            )
            changes_by_action[action_str] = changes_by_action.get(action_str, 0) + 1

        # Count by field
        changes_by_field: Dict[str, int] = {}
        for change in changes:
            field_name = str(change.field)
            changes_by_field[field_name] = changes_by_field.get(field_name, 0) + 1

        # Calculate average confidence
        confidences = [c.confidence for c in changes if c.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "total_changes": total_changes,
            "scenes_affected": scenes_affected,
            "changes_by_action": changes_by_action,
            "changes_by_field": changes_by_field,
            "average_confidence": avg_confidence,
        }
