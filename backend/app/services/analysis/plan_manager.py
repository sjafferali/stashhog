"""Plan management for analysis operations."""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.plan_change import PlanChange, ChangeAction
from app.services.stash_service import StashService
from .models import SceneChanges, ProposedChange, ApplyResult

logger = logging.getLogger(__name__)


class PlanManager:
    """Manage analysis plans and their execution."""
    
    def __init__(self):
        """Initialize plan manager."""
        pass
        
    async def create_plan(
        self,
        name: str,
        changes: List[SceneChanges],
        metadata: Dict[str, Any],
        db: AsyncSession
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
            metadata=metadata,
            status=PlanStatus.DRAFT
        )
        
        db.add(plan)
        await db.flush()  # Get the plan ID
        
        # Create individual change records
        change_count = 0
        for scene_changes in changes:
            if scene_changes.has_changes():
                for change in scene_changes.changes:
                    plan_change = PlanChange(
                        plan_id=plan.id,
                        scene_id=scene_changes.scene_id,
                        field=change.field,
                        action=self._map_action(change.action),
                        current_value=self._serialize_value(change.current_value),
                        proposed_value=self._serialize_value(change.proposed_value),
                        confidence=change.confidence
                    )
                    db.add(plan_change)
                    change_count += 1
        
        # Update metadata with statistics
        plan.add_metadata("total_changes", change_count)
        plan.add_metadata("scene_count", len(changes))
        plan.add_metadata("created_at", datetime.utcnow().isoformat())
        
        await db.commit()
        await db.refresh(plan)
        
        logger.info(f"Created analysis plan '{name}' with {change_count} changes")
        return plan
    
    async def get_plan(
        self,
        plan_id: int,
        db: AsyncSession
    ) -> Optional[AnalysisPlan]:
        """Retrieve a plan with its changes.
        
        Args:
            plan_id: Plan ID
            db: Database session
            
        Returns:
            Analysis plan or None
        """
        query = select(AnalysisPlan).where(
            AnalysisPlan.id == plan_id
        ).options(
            selectinload(AnalysisPlan.changes)
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_plans(
        self,
        db: AsyncSession,
        status: Optional[PlanStatus] = None,
        limit: int = 50,
        offset: int = 0
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
            query = query.where(AnalysisPlan.status == status)
            
        query = query.order_by(AnalysisPlan.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def apply_plan(
        self,
        plan_id: int,
        db: AsyncSession,
        stash_service: StashService,
        apply_filters: Optional[Dict[str, bool]] = None
    ) -> ApplyResult:
        """Apply changes from a plan to Stash.
        
        Args:
            plan_id: Plan to apply
            db: Database session
            stash_service: Stash service for applying changes
            apply_filters: Optional filters for what to apply
            
        Returns:
            Result of applying the plan
        """
        # Get the plan
        plan = await self.get_plan(plan_id, db)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
            
        if not plan.can_be_applied():
            raise ValueError(f"Plan {plan_id} cannot be applied (status: {plan.status})")
        
        # Default filters
        if apply_filters is None:
            apply_filters = {
                "performers": True,
                "studios": True,
                "tags": True,
                "details": True
            }
        
        # Track results
        total_changes = 0
        applied_changes = 0
        failed_changes = 0
        errors = []
        
        # Update plan status
        plan.status = PlanStatus.REVIEWING
        await db.flush()
        
        # Process each change
        for change in plan.changes:
            if not apply_filters.get(change.field, True):
                continue
                
            total_changes += 1
            
            try:
                success = await self.apply_single_change(
                    change,
                    db,
                    stash_service
                )
                
                if success:
                    applied_changes += 1
                else:
                    failed_changes += 1
                    
            except Exception as e:
                failed_changes += 1
                errors.append({
                    "change_id": change.id,
                    "scene_id": change.scene_id,
                    "field": change.field,
                    "error": str(e)
                })
                logger.error(f"Failed to apply change {change.id}: {e}")
        
        # Update plan status
        plan.status = PlanStatus.APPLIED
        plan.applied_at = datetime.utcnow()
        plan.add_metadata("apply_result", {
            "total": total_changes,
            "applied": applied_changes,
            "failed": failed_changes,
            "errors": len(errors)
        })
        
        await db.commit()
        
        return ApplyResult(
            plan_id=plan_id,
            total_changes=total_changes,
            applied_changes=applied_changes,
            failed_changes=failed_changes,
            errors=errors
        )
    
    async def apply_single_change(
        self,
        change: PlanChange,
        db: AsyncSession,
        stash_service: StashService
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
            scene = await stash_service.get_scene(scene_id)
            if not scene:
                logger.error(f"Scene {scene_id} not found")
                return False
            
            # Prepare update data based on field and action
            update_data = {}
            
            if change.field == "studio":
                if change.action == ChangeAction.SET:
                    # Find or create studio
                    studio_name = change.proposed_value
                    if isinstance(studio_name, dict):
                        studio_name = studio_name.get("name", "")
                    
                    if studio_name:
                        studio = await stash_service.find_or_create_studio(studio_name)
                        if studio:
                            update_data["studio_id"] = studio["id"]
                            
            elif change.field == "performers":
                current_ids = [p["id"] for p in scene.get("performers", [])]
                
                if change.action == ChangeAction.ADD:
                    # Add performers
                    new_performers = change.proposed_value
                    if not isinstance(new_performers, list):
                        new_performers = [new_performers]
                    
                    for performer_name in new_performers:
                        if isinstance(performer_name, dict):
                            performer_name = performer_name.get("name", "")
                        
                        if performer_name:
                            performer = await stash_service.find_or_create_performer(performer_name)
                            if performer and performer["id"] not in current_ids:
                                current_ids.append(performer["id"])
                    
                    update_data["performer_ids"] = current_ids
                    
                elif change.action == ChangeAction.REMOVE:
                    # Remove performers
                    remove_names = change.proposed_value
                    if not isinstance(remove_names, list):
                        remove_names = [remove_names]
                    
                    # Get IDs to remove
                    remove_ids = []
                    for name in remove_names:
                        if isinstance(name, dict):
                            name = name.get("name", "")
                        for p in scene.get("performers", []):
                            if p.get("name", "").lower() == name.lower():
                                remove_ids.append(p["id"])
                    
                    update_data["performer_ids"] = [
                        pid for pid in current_ids if pid not in remove_ids
                    ]
                    
            elif change.field == "tags":
                current_ids = [t["id"] for t in scene.get("tags", [])]
                
                if change.action == ChangeAction.ADD:
                    # Add tags
                    new_tags = change.proposed_value
                    if not isinstance(new_tags, list):
                        new_tags = [new_tags]
                    
                    for tag_name in new_tags:
                        if isinstance(tag_name, dict):
                            tag_name = tag_name.get("name", "")
                        
                        if tag_name:
                            tag = await stash_service.find_or_create_tag(tag_name)
                            if tag and tag["id"] not in current_ids:
                                current_ids.append(tag["id"])
                    
                    update_data["tag_ids"] = current_ids
                    
            elif change.field == "details":
                if change.action in [ChangeAction.UPDATE, ChangeAction.SET]:
                    details = change.proposed_value
                    if isinstance(details, dict):
                        details = details.get("text", "")
                    update_data["details"] = details
            
            # Apply the update
            if update_data:
                await stash_service.update_scene(scene_id, update_data)
                
                # Mark change as applied
                change.applied = True
                change.applied_at = datetime.utcnow()
                await db.flush()
                
                return True
            else:
                logger.warning(f"No update data for change {change.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying change {change.id}: {e}")
            return False
    
    async def delete_plan(
        self,
        plan_id: int,
        db: AsyncSession
    ) -> bool:
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
            
        if plan.status == PlanStatus.APPLIED:
            raise ValueError("Cannot delete an applied plan")
        
        await db.delete(plan)
        await db.commit()
        
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
            "set": ChangeAction.SET
        }
        return action_map.get(action.lower(), ChangeAction.SET)
    
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