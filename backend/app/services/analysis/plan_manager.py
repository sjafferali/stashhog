"""Plan management for analysis operations."""

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisPlan, ChangeAction, PlanChange, PlanStatus, Scene
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
        changes: list[SceneChanges],
        metadata: dict[str, Any],
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

    async def create_or_update_plan(
        self,
        name: str,
        scene_changes: SceneChanges,
        metadata: dict[str, Any],
        db: AsyncSession,
        job_id: Optional[str] = None,
    ) -> AnalysisPlan:
        """Create a new plan or update existing plan with scene changes.

        This method is safe for concurrent access from multiple workers.

        Args:
            name: Plan name
            scene_changes: Changes for a single scene
            metadata: Plan metadata
            db: Database session
            job_id: Job ID that's creating this plan

        Returns:
            Created or updated analysis plan
        """
        # Use FOR UPDATE to lock the row during read to prevent concurrent modifications
        existing_plan = None
        if job_id:
            query = (
                select(AnalysisPlan)
                .where(
                    AnalysisPlan.job_id == job_id,
                    AnalysisPlan.status == PlanStatus.PENDING,
                )
                .with_for_update()
            )
            result = await db.execute(query)
            existing_plan = result.scalar_one_or_none()

        if existing_plan:
            # Update existing plan
            existing_plan_id: int = existing_plan.id  # type: ignore[assignment]
            await self.add_changes_to_plan(existing_plan_id, scene_changes, db)

            # Update metadata
            scenes_analyzed = existing_plan.get_metadata("scenes_analyzed", 0) + 1
            existing_plan.add_metadata("scenes_analyzed", scenes_analyzed)
            existing_plan.add_metadata("updated_at", datetime.utcnow().isoformat())

            await db.flush()
            return existing_plan
        else:
            # Create new plan in PENDING status
            # Handle potential race condition where multiple workers try to create the plan
            try:
                logger.info(f"Creating new plan in PENDING status with job_id={job_id}")
                plan = AnalysisPlan(
                    name=name,
                    description=metadata.get("description", ""),
                    plan_metadata=metadata,
                    status=PlanStatus.PENDING,
                    job_id=job_id,
                )

                db.add(plan)
                await db.flush()
                logger.info(f"Flushed new plan to database with id={plan.id}")

                # Add changes if any
                if scene_changes.has_changes():
                    new_plan_id: int = plan.id  # type: ignore[assignment]
                    await self._add_scene_changes(new_plan_id, scene_changes, db)

                # Initialize metadata
                plan.add_metadata("scenes_analyzed", 1)
                plan.add_metadata("created_at", datetime.utcnow().isoformat())

                await db.flush()

                logger.info(f"Created new analysis plan '{name}' in PENDING status")
                return plan
            except IntegrityError:
                # Another worker created the plan, retry to get it
                await db.rollback()
                if job_id:
                    query = (
                        select(AnalysisPlan)
                        .where(
                            AnalysisPlan.job_id == job_id,
                            AnalysisPlan.status == PlanStatus.PENDING,
                        )
                        .with_for_update()
                    )
                    result = await db.execute(query)
                    existing_plan = result.scalar_one_or_none()

                    if existing_plan:
                        retry_plan_id: int = existing_plan.id  # type: ignore[assignment]
                        await self.add_changes_to_plan(retry_plan_id, scene_changes, db)
                        return existing_plan
                raise

    async def add_changes_to_plan(
        self,
        plan_id: int,
        scene_changes: SceneChanges,
        db: AsyncSession,
    ) -> None:
        """Add changes from a scene to an existing plan.

        Args:
            plan_id: Plan ID to add changes to
            scene_changes: Changes for a single scene
            db: Database session
        """
        if not scene_changes.has_changes():
            logger.debug(f"No changes to add for scene {scene_changes.scene_id}")
            return

        logger.info(
            f"Adding {len(scene_changes.changes)} changes from scene {scene_changes.scene_id} to plan {plan_id}"
        )
        await self._add_scene_changes(plan_id, scene_changes, db)

        # Update plan metadata with actual count from database
        plan = await self.get_plan(plan_id, db)
        if plan:
            # Get actual count from database to ensure accuracy
            count_query = select(func.count()).where(PlanChange.plan_id == plan_id)
            result = await db.execute(count_query)
            actual_total = result.scalar() or 0
            plan.add_metadata("total_changes", actual_total)
            logger.info(f"Updated plan {plan_id} total changes to: {actual_total}")

        await db.flush()
        logger.debug(f"Flushed changes for plan {plan_id} to database")

    async def _add_scene_changes(
        self,
        plan_id: int,
        scene_changes: SceneChanges,
        db: AsyncSession,
    ) -> None:
        """Add changes from a single scene to the plan.

        Args:
            plan_id: Plan ID
            scene_changes: Changes for the scene
            db: Database session
        """
        for change in scene_changes.changes:
            plan_change = PlanChange(
                plan_id=plan_id,
                scene_id=scene_changes.scene_id,
                field=change.field,
                action=self._map_action(change.action),
                current_value=self._serialize_value(change.current_value),
                proposed_value=self._serialize_value(change.proposed_value),
                confidence=change.confidence,
            )
            db.add(plan_change)

    async def finalize_plan(
        self,
        plan_id: int,
        db: AsyncSession,
        final_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Finalize a plan when analysis is complete.

        Args:
            plan_id: Plan ID to finalize
            db: Database session
            final_metadata: Final metadata to add
        """
        plan = await self.get_plan(plan_id, db)
        if not plan:
            return

        # Update status from PENDING based on whether any changes have been approved/rejected
        if plan.status == PlanStatus.PENDING:
            # Check if any changes have been approved or rejected
            approved_or_rejected_query = select(func.count()).where(
                PlanChange.plan_id == plan_id,
                or_(PlanChange.accepted.is_(True), PlanChange.rejected.is_(True)),
            )
            result = await db.execute(approved_or_rejected_query)
            approved_or_rejected_count = result.scalar() or 0

            if approved_or_rejected_count > 0:
                plan.status = PlanStatus.REVIEWING  # type: ignore[assignment]
                logger.info(
                    f"Plan {plan_id} has {approved_or_rejected_count} approved/rejected changes, setting status to REVIEWING"
                )
            else:
                plan.status = PlanStatus.DRAFT  # type: ignore[assignment]
                logger.info(
                    f"Plan {plan_id} has no approved/rejected changes, setting status to DRAFT"
                )

        # Add final metadata
        if final_metadata:
            for key, value in final_metadata.items():
                plan.add_metadata(key, value)

        # Refresh change count
        query = select(func.count()).where(PlanChange.plan_id == plan_id)
        result = await db.execute(query)
        total_changes = result.scalar() or 0
        plan.add_metadata("total_changes", total_changes)

        await db.flush()
        logger.info(f"Finalized plan {plan_id} with {total_changes} changes")

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
    ) -> list[AnalysisPlan]:
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
        apply_filters: Optional[dict[str, bool]] = None,
        change_ids: Optional[list[int]] = None,
        progress_callback: Optional[Any] = None,
    ) -> ApplyResult:
        """Apply changes from a plan to Stash.

        Args:
            plan_id: Plan to apply
            db: Database session
            stash_service: Stash service for applying changes
            apply_filters: Optional filters for what to apply
            change_ids: Optional list of specific change IDs to apply
            progress_callback: Optional callback for progress updates

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
            changes, apply_filters, db, stash_service, change_ids, progress_callback
        )

        # Finalize plan application
        await self._finalize_plan_application(plan, result_data, db)

        return ApplyResult(
            plan_id=plan_id,
            total_changes=result_data["total_changes"],
            applied_changes=result_data["applied_changes"],
            failed_changes=result_data["failed_changes"],
            errors=result_data["errors"],
            modified_scene_ids=result_data.get("modified_scene_ids", []),
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

    def _get_default_apply_filters(self) -> dict[str, bool]:
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
    ) -> list[PlanChange]:
        """Get all changes for a plan."""
        changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
        result = await db.execute(changes_query)
        return list(result.scalars().all())

    async def _process_plan_changes(
        self,
        changes: list[PlanChange],
        apply_filters: dict[str, bool],
        db: AsyncSession,
        stash_service: StashService,
        change_ids: Optional[list[int]] = None,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Process all changes in a plan."""
        total_changes = 0
        applied_changes = 0
        failed_changes = 0
        errors = []
        modified_scene_ids = set()

        # Count changes to apply first
        changes_to_apply = [
            change
            for change in changes
            if self._should_apply_change(change, apply_filters, change_ids)
        ]
        total_changes = len(changes_to_apply)

        # Report initial progress
        if progress_callback and total_changes > 0:
            await progress_callback(10, f"Applied 0/{total_changes} changes")

        for i, change in enumerate(changes_to_apply):
            try:
                success = await self.apply_single_change(change, db, stash_service)
                if success:
                    applied_changes += 1
                    # Track the scene ID that was modified
                    modified_scene_ids.add(str(change.scene_id))
                else:
                    failed_changes += 1
            except Exception as e:
                failed_changes += 1
                errors.append(self._create_error_record(change, e))
                logger.error(f"Failed to apply change {change.id}: {e}")

            # Report progress after each change
            if progress_callback and total_changes > 0:
                progress = 10 + int((i + 1) / total_changes * 85)  # 10-95%
                await progress_callback(
                    progress, f"Applied {i + 1}/{total_changes} changes"
                )

        return {
            "total_changes": total_changes,
            "applied_changes": applied_changes,
            "failed_changes": failed_changes,
            "errors": errors,
            "modified_scene_ids": list(modified_scene_ids),
        }

    def _should_apply_change(
        self,
        change: PlanChange,
        apply_filters: dict[str, bool],
        change_ids: Optional[list[int]] = None,
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
    ) -> dict[str, Any]:
        """Create an error record for a failed change."""
        return {
            "change_id": change.id,
            "scene_id": change.scene_id,
            "field": change.field,
            "error": str(error),
        }

    async def _finalize_plan_application(
        self, plan: AnalysisPlan, result_data: dict[str, Any], db: AsyncSession
    ) -> None:
        """Finalize plan application with status and metadata updates."""
        # Add metadata about this apply operation
        plan.add_metadata(
            "apply_result",
            {
                "total": result_data["total_changes"],
                "applied": result_data["applied_changes"],
                "failed": result_data["failed_changes"],
                "errors": len(result_data["errors"]),
            },
        )

        # For async context, we need to manually calculate the status
        # instead of using the model's method which uses lazy loading
        await self._update_plan_status_async(plan, db)

        await db.flush()

    async def _update_plan_status_async(
        self, plan: AnalysisPlan, db: AsyncSession
    ) -> None:
        """Update plan status based on changes using async queries."""
        # Get change counts using async queries
        base_query = select(func.count()).where(PlanChange.plan_id == plan.id)

        # Total changes
        total_result = await db.execute(base_query)
        total = total_result.scalar() or 0

        if total == 0:
            return

        # Applied changes
        applied_result = await db.execute(
            select(func.count()).where(
                PlanChange.plan_id == plan.id, PlanChange.applied.is_(True)
            )
        )
        applied = applied_result.scalar() or 0

        # Accepted changes
        accepted_result = await db.execute(
            select(func.count()).where(
                PlanChange.plan_id == plan.id, PlanChange.accepted.is_(True)
            )
        )
        accepted = accepted_result.scalar() or 0

        # Rejected changes
        rejected_result = await db.execute(
            select(func.count()).where(
                PlanChange.plan_id == plan.id, PlanChange.rejected.is_(True)
            )
        )
        rejected = rejected_result.scalar() or 0

        # Pending changes
        pending_result = await db.execute(
            select(func.count()).where(
                PlanChange.plan_id == plan.id,
                PlanChange.accepted.is_(False),
                PlanChange.rejected.is_(False),
            )
        )
        pending = pending_result.scalar() or 0

        # Update status based on counts (same logic as model method)
        if plan.status == PlanStatus.DRAFT and (accepted > 0 or rejected > 0):
            plan.status = PlanStatus.REVIEWING  # type: ignore[assignment]

        # Plan is fully applied when all accepted changes are applied
        # and there are no pending changes
        if accepted > 0 and accepted == applied and pending == 0:
            plan.status = PlanStatus.APPLIED  # type: ignore[assignment]
            plan.applied_at = datetime.utcnow()  # type: ignore[assignment]

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

            # Special handling for markers - they are created directly, not via scene update
            if change.field == "markers":
                await self._prepare_markers_update(change, scene, stash_service)
                # Mark change as applied
                change.applied = True  # type: ignore[assignment]
                change.applied_at = datetime.utcnow()  # type: ignore[assignment]
                await db.flush()
                return True

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
        self, change: PlanChange, scene: dict, stash_service: StashService
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
        self, change: PlanChange, scene: dict, stash_service: StashService
    ) -> dict[str, Any]:
        """Prepare performers update data."""
        current_ids = [p["id"] for p in scene.get("performers", [])]

        if change.action == ChangeAction.ADD:
            new_ids = await self._add_performers(
                change.proposed_value, current_ids, stash_service
            )
            return {"performer_ids": new_ids}
        elif change.action == ChangeAction.REMOVE:
            remaining_ids = self._remove_performers(
                change.proposed_value, current_ids, scene.get("performers", [])
            )
            return {"performer_ids": remaining_ids}
        return {}

    async def _add_performers(
        self, new_performers: Any, current_ids: list[str], stash_service: StashService
    ) -> list[str]:
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
        self, remove_names: Any, current_ids: list[str], current_performers: list[dict]
    ) -> list[str]:
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
        self, change: PlanChange, scene: dict, stash_service: StashService
    ) -> dict[str, Any]:
        """Prepare tags update data."""
        current_ids = [t["id"] for t in scene.get("tags", [])]
        current_tags = scene.get("tags", [])

        if change.action == ChangeAction.ADD:
            new_ids = await self._add_tags(
                change.proposed_value, current_ids, stash_service
            )
            return {"tag_ids": new_ids}
        elif change.action == ChangeAction.REMOVE:
            remaining_ids = await self._remove_tags(
                change.current_value, current_ids, current_tags, stash_service
            )
            return {"tag_ids": remaining_ids}
        return {}

    async def _add_tags(
        self, new_tags: Any, current_ids: list[str], stash_service: StashService
    ) -> list[str]:
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

    async def _remove_tags(
        self,
        remove_tags: Any,
        current_ids: list[str],
        current_tags: list[dict],
        stash_service: StashService,
    ) -> list[str]:
        """Remove tags from current list."""
        if not isinstance(remove_tags, list):
            remove_tags = [remove_tags]

        # Get IDs to remove
        remove_ids = []
        for tag_name in remove_tags:
            if isinstance(tag_name, dict):
                tag_name = tag_name.get("name", "")

            # Find the tag ID to remove
            for tag in current_tags:
                if tag.get("name", "").lower() == tag_name.lower():
                    remove_ids.append(tag["id"])
                    break
            else:
                # If not in current tags, try to find it via stash service
                found_tag = await stash_service.find_tag(tag_name)
                if found_tag:
                    remove_ids.append(found_tag["id"])

        return [tid for tid in current_ids if tid not in remove_ids]

    def _prepare_details_update(self, change: PlanChange) -> dict[str, Any]:
        """Prepare details update data."""
        if change.action in [ChangeAction.UPDATE, ChangeAction.SET, ChangeAction.ADD]:
            details = change.proposed_value
            if isinstance(details, dict):
                details = details.get("text", "")
            return {"details": details}
        return {}

    async def _prepare_markers_update(
        self, change: PlanChange, scene: dict, stash_service: StashService
    ) -> dict[str, Any]:
        """Prepare markers update data.

        Note: Markers are handled differently - they need to be created individually
        rather than updated on the scene.
        """
        if change.action == ChangeAction.ADD:
            await self._add_markers(change, scene, stash_service)
        elif change.action == ChangeAction.REMOVE:
            await self._remove_marker(change, scene, stash_service)

        # Return empty dict as markers are handled separately
        return {}

    async def _add_markers(
        self, change: PlanChange, scene: dict, stash_service: StashService
    ) -> None:
        """Add markers to a scene."""
        from typing import cast

        markers_value = cast(Any, change.proposed_value)
        markers_to_create: list[dict[str, Any]]
        if isinstance(markers_value, list):
            markers_to_create = markers_value
        else:
            # Single marker or None
            markers_to_create = [markers_value] if markers_value else []

        for marker_data in markers_to_create:
            await self._create_single_marker(marker_data, scene, stash_service)

    async def _create_single_marker(
        self, marker_data: dict, scene: dict, stash_service: StashService
    ) -> None:
        """Create a single marker."""
        # Ensure scene_id is set correctly
        marker_data["scene_id"] = scene["id"]

        # Convert tag names to tag IDs
        marker_tags = await self._get_marker_tags(marker_data, stash_service)

        # Only create marker if we have at least one tag
        if not marker_tags:
            logger.warning(
                f"Skipping marker creation - no tags found for marker at {marker_data.get('seconds', 0)}s"
            )
            return

        # Create marker with proper format
        marker_to_create = self._build_marker_data(scene, marker_data, marker_tags)

        try:
            await stash_service.create_marker(marker_to_create)  # type: ignore[arg-type]
            logger.info(
                f"Created marker for scene {scene['id']} at {marker_data.get('seconds', 0)}s"
            )
        except Exception as e:
            logger.error(f"Failed to create marker: {e}")
            raise

    async def _get_marker_tags(
        self, marker_data: dict, stash_service: StashService
    ) -> list[str]:
        """Get tag IDs for marker."""
        from app.core.database import AsyncSessionLocal

        marker_tags = []
        for tag_name in marker_data.get("tags", []):
            async with AsyncSessionLocal() as db:
                tag_id = await stash_service.find_or_create_tag(tag_name, db)
                if tag_id:
                    marker_tags.append(tag_id)
        return marker_tags

    def _build_marker_data(
        self, scene: dict, marker_data: dict, marker_tags: list[str]
    ) -> dict[str, Any]:
        """Build marker data for creation."""
        marker_to_create = {
            "scene_id": scene["id"],
            "seconds": marker_data.get("seconds", 0),
            "title": marker_data.get("title", ""),
            "tag_ids": marker_tags,
        }

        # Add end_seconds if provided
        if "end_seconds" in marker_data:
            marker_to_create["end_seconds"] = marker_data["end_seconds"]

        return marker_to_create

    async def _remove_marker(
        self, change: PlanChange, scene: dict, stash_service: StashService
    ) -> None:
        """Remove a marker from a scene."""
        marker_to_remove = change.current_value
        if not marker_to_remove or not isinstance(marker_to_remove, dict):
            return

        marker_id = marker_to_remove.get("id")
        if not marker_id:
            logger.warning("Marker to remove has no ID")
            return

        try:
            await stash_service.delete_marker(marker_id)
            logger.info(f"Deleted marker {marker_id} for scene {scene['id']}")
        except Exception as e:
            logger.error(f"Failed to delete marker {marker_id}: {e}")
            raise

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
    ) -> dict[str, Any]:
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
        changes_by_action: dict[str, int] = {}
        for change in changes:
            action_str = (
                change.action.value
                if hasattr(change.action, "value")
                else str(change.action)
            )
            changes_by_action[action_str] = changes_by_action.get(action_str, 0) + 1

        # Count by field
        changes_by_field: dict[str, int] = {}
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
