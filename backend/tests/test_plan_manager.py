"""
Tests for analysis plan manager.

This module tests plan CRUD operations, plan execution, and change management.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, call

import pytest
from sqlalchemy import select

from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.plan_change import ChangeAction, ChangeStatus, PlanChange
from app.models.scene import Scene
from app.services.analysis.models import ProposedChange, SceneChanges
from app.services.analysis.plan_manager import PlanManager
from app.services.stash_service import StashService
from tests.helpers import create_test_scene


class TestPlanCreation:
    """Test cases for plan creation."""

    @pytest.mark.asyncio
    async def test_create_plan_empty_changes(self, test_async_session):
        """Test creating a plan with no changes."""
        manager = PlanManager()

        changes = []
        metadata = {"description": "Empty plan"}

        plan = await manager.create_plan(
            "Empty Plan", changes, metadata, test_async_session
        )

        assert plan.name == "Empty Plan"
        assert plan.description == "Empty plan"
        assert plan.status == PlanStatus.DRAFT
        assert plan.plan_metadata["total_changes"] == 0
        assert plan.plan_metadata["scene_count"] == 0

    @pytest.mark.asyncio
    async def test_create_plan_with_changes(self, test_async_session):
        """Test creating a plan with multiple scene changes."""
        manager = PlanManager()

        # Create test scenes
        scene1 = create_test_scene(
            id="scene1",
            title="Scene 1",
            paths=[],
            stash_updated_at=datetime.utcnow(),
        )
        scene2 = create_test_scene(
            id="scene2",
            title="Scene 2",
            paths=[],
            stash_updated_at=datetime.utcnow(),
        )
        test_async_session.add_all([scene1, scene2])
        await test_async_session.commit()

        # Create changes
        changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1",
                changes=[
                    ProposedChange(
                        field="title",
                        action="update",
                        current_value="Scene 1",
                        proposed_value="Updated Scene 1",
                        confidence=0.9,
                    ),
                    ProposedChange(
                        field="details",
                        action="add",
                        current_value=None,
                        proposed_value="New details",
                        confidence=0.8,
                    ),
                ],
            ),
            SceneChanges(
                scene_id="scene2",
                scene_title="Scene 2",
                scene_path="/path/to/scene2",
                changes=[
                    ProposedChange(
                        field="performers",
                        action="add",
                        current_value=[],
                        proposed_value=["performer1", "performer2"],
                        confidence=0.85,
                    )
                ],
            ),
        ]

        metadata = {
            "description": "Test plan with changes",
            "analysis_settings": {"confidence_threshold": 0.7},
        }

        plan = await manager.create_plan(
            "Test Plan", changes, metadata, test_async_session
        )

        assert plan.name == "Test Plan"
        assert plan.status == PlanStatus.DRAFT
        assert plan.plan_metadata["total_changes"] == 3
        assert plan.plan_metadata["scene_count"] == 2
        assert "created_at" in plan.plan_metadata

        # Verify scenes marked as analyzed
        scene1_result = await test_async_session.execute(
            select(Scene).where(Scene.id == "scene1")
        )
        scene1_updated = scene1_result.scalar_one()
        assert scene1_updated.analyzed is True

    @pytest.mark.asyncio
    async def test_create_plan_no_actual_changes(self, test_async_session):
        """Test creating a plan where scenes have no changes."""
        manager = PlanManager()

        # Create test scene
        scene = create_test_scene(
            id="scene1",
            title="Scene 1",
            paths=[],
            analyzed=False,
            stash_updated_at=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Scene with no changes
        changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1",
                changes=[],
            )
        ]

        metadata = {"description": "Plan with no actual changes"}

        plan = await manager.create_plan(
            "No Changes Plan", changes, metadata, test_async_session
        )

        assert plan.plan_metadata["total_changes"] == 0
        assert plan.plan_metadata["scene_count"] == 1

        # Scene should still be marked as analyzed
        scene_result = await test_async_session.execute(
            select(Scene).where(Scene.id == "scene1")
        )
        scene_updated = scene_result.scalar_one()
        assert scene_updated.analyzed is True

    @pytest.mark.asyncio
    async def test_create_plan_with_complex_values(self, test_async_session):
        """Test creating a plan with complex field values."""
        manager = PlanManager()

        # Create test scene
        scene = create_test_scene(
            id="scene1",
            title="Scene 1",
            paths=[],
            stash_updated_at=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Complex changes including lists and None values
        changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1",
                changes=[
                    ProposedChange(
                        field="tags",
                        action="update",
                        current_value=["tag1", "tag2"],
                        proposed_value=["tag1", "tag2", "tag3"],
                        confidence=0.9,
                    ),
                    ProposedChange(
                        field="rating",
                        action="remove",
                        current_value=5,
                        proposed_value=None,
                        confidence=0.7,
                    ),
                ],
            )
        ]

        metadata = {"description": "Complex value test"}

        plan = await manager.create_plan(
            "Complex Plan", changes, metadata, test_async_session
        )

        # Verify change records created correctly
        change_query = select(PlanChange).where(PlanChange.plan_id == plan.id)
        result = await test_async_session.execute(change_query)
        plan_changes = result.scalars().all()

        assert len(plan_changes) == 2

        # Check serialization
        tags_change = next(c for c in plan_changes if c.field == "tags")
        assert tags_change.action == ChangeAction.UPDATE
        assert isinstance(tags_change.current_value, list)
        assert tags_change.proposed_value == ["tag1", "tag2", "tag3"]


class TestPlanRetrieval:
    """Test cases for plan retrieval."""

    @pytest.mark.asyncio
    async def test_get_plan_exists(self, test_async_session):
        """Test retrieving an existing plan."""
        manager = PlanManager()

        # Create a plan
        plan = AnalysisPlan(
            name="Test Plan",
            description="Test",
            status=PlanStatus.DRAFT,
            plan_metadata={},
        )
        test_async_session.add(plan)
        await test_async_session.commit()

        # Retrieve it
        retrieved = await manager.get_plan(plan.id, test_async_session)

        assert retrieved is not None
        assert retrieved.id == plan.id
        assert retrieved.name == "Test Plan"

    @pytest.mark.asyncio
    async def test_get_plan_not_exists(self, test_async_session):
        """Test retrieving a non-existent plan."""
        manager = PlanManager()

        retrieved = await manager.get_plan(999, test_async_session)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_plans_empty(self, test_async_session):
        """Test listing plans when none exist."""
        manager = PlanManager()

        plans = await manager.list_plans(test_async_session)

        assert plans == []

    @pytest.mark.asyncio
    async def test_list_plans_with_filter(self, test_async_session):
        """Test listing plans with status filter."""
        manager = PlanManager()

        # Create plans with different statuses
        plan1 = AnalysisPlan(
            name="Draft Plan", status=PlanStatus.DRAFT, plan_metadata={}
        )
        plan2 = AnalysisPlan(
            name="Applied Plan", status=PlanStatus.APPLIED, plan_metadata={}
        )
        plan3 = AnalysisPlan(
            name="Another Draft", status=PlanStatus.DRAFT, plan_metadata={}
        )

        test_async_session.add_all([plan1, plan2, plan3])
        await test_async_session.commit()

        # Filter by DRAFT status
        draft_plans = await manager.list_plans(
            test_async_session, status=PlanStatus.DRAFT
        )

        assert len(draft_plans) == 2
        assert all(p.status == PlanStatus.DRAFT for p in draft_plans)

        # Filter by COMPLETE status
        applied_plans = await manager.list_plans(
            test_async_session, status=PlanStatus.APPLIED
        )

        assert len(applied_plans) == 1
        assert applied_plans[0].status == PlanStatus.APPLIED

    @pytest.mark.asyncio
    async def test_list_plans_pagination(self, test_async_session):
        """Test listing plans with pagination."""
        manager = PlanManager()

        # Create multiple plans
        plans = [
            AnalysisPlan(
                name=f"Plan {i}",
                status=PlanStatus.DRAFT,
                plan_metadata={},
                created_at=datetime.utcnow(),
            )
            for i in range(10)
        ]

        test_async_session.add_all(plans)
        await test_async_session.commit()

        # Test pagination
        page1 = await manager.list_plans(test_async_session, limit=5, offset=0)
        page2 = await manager.list_plans(test_async_session, limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id


class TestPlanApplication:
    """Test cases for plan application."""

    @pytest.mark.asyncio
    async def test_apply_plan_not_found(self, test_async_session):
        """Test applying a non-existent plan."""
        manager = PlanManager()
        stash_service = Mock(spec=StashService)

        with pytest.raises(ValueError, match="Plan 999 not found"):
            await manager.apply_plan(999, test_async_session, stash_service)

    @pytest.mark.asyncio
    async def test_apply_plan_invalid_status(self, test_async_session):
        """Test applying a plan with invalid status."""
        manager = PlanManager()
        stash_service = Mock(spec=StashService)

        # Create a plan with COMPLETE status
        plan = AnalysisPlan(
            name="Applied Plan", status=PlanStatus.APPLIED, plan_metadata={}
        )
        test_async_session.add(plan)
        await test_async_session.commit()

        with pytest.raises(ValueError, match="cannot be applied"):
            await manager.apply_plan(plan.id, test_async_session, stash_service)

    @pytest.mark.asyncio
    async def test_apply_plan_success(self, test_async_session):
        """Test successfully applying a plan."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.update_scene = AsyncMock(return_value=True)
        stash_service.get_scene = AsyncMock(
            return_value={
                "id": "scene1",
                "title": "Old Title",
                "details": "Old details",
            }
        )

        # Create a plan with changes
        plan = AnalysisPlan(name="Test Plan", status=PlanStatus.DRAFT, plan_metadata={})
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add changes
        change1 = PlanChange(
            plan_id=plan.id,
            scene_id="scene1",
            field="title",
            action=ChangeAction.UPDATE,
            current_value="Old Title",
            proposed_value="New Title",
            confidence=0.9,
            status=ChangeStatus.APPROVED,
        )
        change2 = PlanChange(
            plan_id=plan.id,
            scene_id="scene1",
            field="details",
            action=ChangeAction.ADD,
            current_value=None,
            proposed_value="Scene details",
            confidence=0.8,
            status=ChangeStatus.APPROVED,
        )

        test_async_session.add_all([change1, change2])
        await test_async_session.commit()

        # Apply the plan
        result = await manager.apply_plan(plan.id, test_async_session, stash_service)

        assert result.total_changes == 2
        assert result.applied_changes == 2
        assert result.failed_changes == 0
        assert result.errors == []

        # Verify stash service called
        assert stash_service.update_scene.call_count == 2

    @pytest.mark.asyncio
    async def test_apply_plan_with_filters(self, test_async_session):
        """Test applying a plan with field filters."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.update_scene = AsyncMock(return_value=True)
        stash_service.get_scene = AsyncMock(
            return_value={
                "id": "scene1",
                "title": "Old Title",
                "details": "Old details",
                "rating": 3,
            }
        )

        # Create a plan
        plan = AnalysisPlan(name="Test Plan", status=PlanStatus.DRAFT, plan_metadata={})
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add various changes
        changes = [
            PlanChange(
                plan_id=plan.id,
                scene_id="scene1",
                field="performers",
                action=ChangeAction.ADD,
                current_value=[],
                proposed_value=["performer1"],
                confidence=0.9,
                status=ChangeStatus.APPROVED,
            ),
            PlanChange(
                plan_id=plan.id,
                scene_id="scene1",
                field="tags",
                action=ChangeAction.ADD,
                current_value=[],
                proposed_value=["tag1"],
                confidence=0.8,
                status=ChangeStatus.APPROVED,
            ),
            PlanChange(
                plan_id=plan.id,
                scene_id="scene1",
                field="details",
                action=ChangeAction.UPDATE,
                current_value="Old",
                proposed_value="New",
                confidence=0.7,
                status=ChangeStatus.APPROVED,
            ),
        ]

        test_async_session.add_all(changes)
        await test_async_session.commit()

        # Apply with filters - only performers and tags
        filters = {"performers": True, "tags": True, "details": False}

        result = await manager.apply_plan(
            plan.id, test_async_session, stash_service, apply_filters=filters
        )

        # Should only apply 2 changes (performers and tags)
        assert result.total_changes == 2
        assert result.applied_changes == 2
        assert stash_service.update_scene.call_count == 2

    @pytest.mark.asyncio
    async def test_apply_plan_partial_failure(self, test_async_session):
        """Test applying a plan with some failures."""
        manager = PlanManager()

        # Create mock stash service that fails on second call
        stash_service = Mock(spec=StashService)
        stash_service.update_scene = AsyncMock(
            side_effect=[True, Exception("Update failed"), True]
        )
        stash_service.get_scene = AsyncMock(
            side_effect=[
                {"id": "scene0", "title": "Old 0"},
                {"id": "scene1", "title": "Old 1"},
                {"id": "scene2", "title": "Old 2"},
            ]
        )

        # Create a plan with changes
        plan = AnalysisPlan(name="Test Plan", status=PlanStatus.DRAFT, plan_metadata={})
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add changes
        for i in range(3):
            change = PlanChange(
                plan_id=plan.id,
                scene_id=f"scene{i}",
                field="title",
                action=ChangeAction.UPDATE,
                current_value=f"Old {i}",
                proposed_value=f"New {i}",
                confidence=0.9,
                status=ChangeStatus.APPROVED,
            )
            test_async_session.add(change)

        await test_async_session.commit()

        # Apply the plan
        result = await manager.apply_plan(plan.id, test_async_session, stash_service)

        assert result.total_changes == 3
        assert result.applied_changes == 2
        assert result.failed_changes == 1
        assert len(result.errors) == 1
        assert "Update failed" in result.errors[0]["error"]


class TestHelperMethods:
    """Test cases for helper methods."""

    def test_map_action(self):
        """Test action mapping."""
        manager = PlanManager()

        assert manager._map_action("add") == ChangeAction.ADD
        assert manager._map_action("update") == ChangeAction.UPDATE
        assert manager._map_action("remove") == ChangeAction.REMOVE
        assert manager._map_action("invalid") == ChangeAction.UPDATE  # default

    def test_serialize_value(self):
        """Test value serialization."""
        manager = PlanManager()

        # Test various types
        assert manager._serialize_value("string") == "string"
        assert manager._serialize_value(123) == 123
        assert manager._serialize_value(True) is True
        assert manager._serialize_value(None) is None
        assert manager._serialize_value([1, 2, 3]) == [1, 2, 3]
        assert manager._serialize_value({"key": "value"}) == {"key": "value"}

        # Test edge cases
        assert manager._serialize_value([]) == []
        assert manager._serialize_value({}) == {}


class TestPlanExecution:
    """Test cases for plan execution management."""

    @pytest.mark.asyncio
    async def test_update_plan_status(self, test_async_session):
        """Test updating plan status."""
        manager = PlanManager()

        # Create a plan
        plan = AnalysisPlan(name="Test Plan", status=PlanStatus.DRAFT, plan_metadata={})
        test_async_session.add(plan)
        await test_async_session.commit()

        # Update status
        await manager.update_plan_status(
            plan.id, PlanStatus.REVIEWING, test_async_session
        )

        # Verify update
        await test_async_session.refresh(plan)
        assert plan.status == PlanStatus.REVIEWING

    @pytest.mark.asyncio
    async def test_delete_plan(self, test_async_session):
        """Test deleting a plan."""
        manager = PlanManager()

        # Create a plan with changes
        plan = AnalysisPlan(name="Test Plan", status=PlanStatus.DRAFT, plan_metadata={})
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add a change
        change = PlanChange(
            plan_id=plan.id,
            scene_id="scene1",
            field="title",
            action=ChangeAction.UPDATE,
            current_value="Old",
            proposed_value="New",
            confidence=0.9,
        )
        test_async_session.add(change)
        await test_async_session.commit()

        # Delete the plan
        await manager.delete_plan(plan.id, test_async_session)

        # Verify deletion
        result = await test_async_session.execute(
            select(AnalysisPlan).where(AnalysisPlan.id == plan.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify cascade deletion of changes
        change_result = await test_async_session.execute(
            select(PlanChange).where(PlanChange.plan_id == plan.id)
        )
        assert change_result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_applied_plan_fails(self, test_async_session):
        """Test that deleting an applied plan fails."""
        manager = PlanManager()

        # Create a completed plan
        plan = AnalysisPlan(
            name="Applied Plan", status=PlanStatus.APPLIED, plan_metadata={}
        )
        test_async_session.add(plan)
        await test_async_session.commit()

        # Try to delete the plan
        with pytest.raises(ValueError, match="Cannot delete an applied plan"):
            await manager.delete_plan(plan.id, test_async_session)

    @pytest.mark.asyncio
    async def test_get_plan_statistics(self, test_async_session):
        """Test getting plan statistics."""
        manager = PlanManager()

        # Create a plan with various changes
        plan = AnalysisPlan(name="Test Plan", status=PlanStatus.DRAFT, plan_metadata={})
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add changes with different actions and fields
        changes_data = [
            ("scene1", "title", ChangeAction.UPDATE, 0.9),
            ("scene1", "performers", ChangeAction.ADD, 0.8),
            ("scene2", "tags", ChangeAction.ADD, 0.85),
            ("scene2", "details", ChangeAction.UPDATE, 0.7),
            ("scene3", "rating", ChangeAction.REMOVE, 0.95),
        ]

        for scene_id, field, action, confidence in changes_data:
            change = PlanChange(
                plan_id=plan.id,
                scene_id=scene_id,
                field=field,
                action=action,
                current_value="old",
                proposed_value="new",
                confidence=confidence,
            )
            test_async_session.add(change)

        await test_async_session.commit()

        # Get statistics
        stats = await manager.get_plan_statistics(plan.id, test_async_session)

        assert stats["total_changes"] == 5
        assert stats["scenes_affected"] == 3
        assert stats["changes_by_action"] == {"add": 2, "update": 2, "remove": 1}
        assert stats["changes_by_field"] == {
            "title": 1,
            "performers": 1,
            "tags": 1,
            "details": 1,
            "rating": 1,
        }
        assert stats["average_confidence"] == pytest.approx(0.84, rel=0.01)

    @pytest.mark.asyncio
    async def test_apply_single_change_success(self, test_async_session):
        """Test applying a single change successfully."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.get_scene = AsyncMock(
            return_value={
                "id": "scene1",
                "title": "Old Title",
                "details": "Old details",
            }
        )
        stash_service.update_scene = AsyncMock(return_value=True)

        # Create a change
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="title",
            action=ChangeAction.UPDATE,
            current_value="Old Title",
            proposed_value="New Title",
            confidence=0.9,
        )
        test_async_session.add(change)
        await test_async_session.commit()

        # Apply the change
        result = await manager.apply_single_change(
            change, test_async_session, stash_service
        )

        assert result is True
        assert change.applied is True
        assert change.applied_at is not None
        stash_service.update_scene.assert_called_once_with(
            "scene1", {"title": "New Title"}
        )

    @pytest.mark.asyncio
    async def test_apply_single_change_scene_not_found(self, test_async_session):
        """Test applying a change when scene is not found."""
        manager = PlanManager()

        # Create mock stash service that returns None
        stash_service = Mock(spec=StashService)
        stash_service.get_scene = AsyncMock(return_value=None)

        # Create a change
        change = PlanChange(
            plan_id=1,
            scene_id="missing_scene",
            field="title",
            action=ChangeAction.UPDATE,
            current_value="Old",
            proposed_value="New",
            confidence=0.9,
        )

        # Apply the change
        result = await manager.apply_single_change(
            change, test_async_session, stash_service
        )

        assert result is False
        # Check that change wasn't marked as applied
        assert change.applied is None or change.applied is False

    @pytest.mark.asyncio
    async def test_prepare_studio_update(self, test_async_session):
        """Test preparing studio update data."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.find_studio = AsyncMock(return_value=None)
        stash_service.create_studio = AsyncMock(return_value={"id": "studio123"})

        # Test SET action with new studio
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="studio",
            action=ChangeAction.SET,
            proposed_value="New Studio",
            confidence=0.9,
        )

        update_data = await manager._prepare_studio_update(change, stash_service)

        assert update_data == {"studio_id": "studio123"}
        stash_service.find_studio.assert_called_once_with("New Studio")
        stash_service.create_studio.assert_called_once_with("New Studio")

    @pytest.mark.asyncio
    async def test_prepare_studio_update_existing(self, test_async_session):
        """Test preparing studio update with existing studio."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.find_studio = AsyncMock(return_value={"id": "existing_studio"})

        # Test SET action with existing studio
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="studio",
            action=ChangeAction.SET,
            proposed_value={"name": "Existing Studio"},
            confidence=0.9,
        )

        update_data = await manager._prepare_studio_update(change, stash_service)

        assert update_data == {"studio_id": "existing_studio"}
        stash_service.find_studio.assert_called_once_with("Existing Studio")

    @pytest.mark.asyncio
    async def test_prepare_performers_update_add(self, test_async_session):
        """Test preparing performers update for ADD action."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.find_performer = AsyncMock(side_effect=[None, {"id": "perf2"}])
        stash_service.create_performer = AsyncMock(return_value={"id": "perf1"})

        # Current scene data
        scene = {
            "id": "scene1",
            "performers": [{"id": "existing_perf", "name": "Existing Performer"}],
        }

        # Test ADD action
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="performers",
            action=ChangeAction.ADD,
            proposed_value=["New Performer 1", "Existing Performer 2"],
            confidence=0.9,
        )

        update_data = await manager._prepare_performers_update(
            change, scene, stash_service
        )

        assert update_data == {"performer_ids": ["existing_perf", "perf1", "perf2"]}
        assert stash_service.find_performer.call_count == 2
        assert stash_service.create_performer.call_count == 1

    @pytest.mark.asyncio
    async def test_prepare_performers_update_remove(self, test_async_session):
        """Test preparing performers update for REMOVE action."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)

        # Current scene data
        scene = {
            "id": "scene1",
            "performers": [
                {"id": "perf1", "name": "Performer 1"},
                {"id": "perf2", "name": "Performer 2"},
                {"id": "perf3", "name": "Performer 3"},
            ],
        }

        # Test REMOVE action
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="performers",
            action=ChangeAction.REMOVE,
            proposed_value=["Performer 2"],
            confidence=0.9,
        )

        update_data = await manager._prepare_performers_update(
            change, scene, stash_service
        )

        assert update_data == {"performer_ids": ["perf1", "perf3"]}

    @pytest.mark.asyncio
    async def test_prepare_tags_update(self, test_async_session):
        """Test preparing tags update."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.find_tag = AsyncMock(side_effect=[None, {"id": "tag2"}])
        stash_service.create_tag = AsyncMock(return_value={"id": "tag1"})

        # Current scene data
        scene = {
            "id": "scene1",
            "tags": [{"id": "existing_tag", "name": "Existing Tag"}],
        }

        # Test ADD action
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="tags",
            action=ChangeAction.ADD,
            proposed_value=["New Tag", {"name": "Another Tag"}],
            confidence=0.9,
        )

        update_data = await manager._prepare_tags_update(change, scene, stash_service)

        assert update_data == {"tag_ids": ["existing_tag", "tag1", "tag2"]}

    @pytest.mark.asyncio
    async def test_prepare_details_update(self, test_async_session):
        """Test preparing details update."""
        manager = PlanManager()

        # Test UPDATE action
        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="details",
            action=ChangeAction.UPDATE,
            proposed_value="New scene details",
            confidence=0.9,
        )

        update_data = manager._prepare_details_update(change)

        assert update_data == {"details": "New scene details"}

        # Test with dict value
        change.proposed_value = {"text": "Details from dict"}
        update_data = manager._prepare_details_update(change)

        assert update_data == {"details": "Details from dict"}


class TestBulkOperations:
    """Test cases for bulk operations and edge cases."""

    @pytest.mark.asyncio
    async def test_create_plan_with_many_changes(self, test_async_session):
        """Test creating a plan with many changes to ensure bulk operations work."""
        manager = PlanManager()

        # Create many test scenes
        scenes = []
        for i in range(50):
            scene = create_test_scene(
                id=f"scene{i}",
                title=f"Scene {i}",
                paths=[],
                stash_updated_at=datetime.utcnow(),
            )
            scenes.append(scene)
        test_async_session.add_all(scenes)
        await test_async_session.commit()

        # Create changes for all scenes
        changes = []
        for i in range(50):
            scene_changes = SceneChanges(
                scene_id=f"scene{i}",
                scene_title=f"Scene {i}",
                scene_path=f"/path/to/scene{i}",
                changes=[
                    ProposedChange(
                        field="title",
                        action="update",
                        current_value=f"Scene {i}",
                        proposed_value=f"Updated Scene {i}",
                        confidence=0.9,
                    ),
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=[],
                        proposed_value=[f"tag{i}", f"tag{i + 1}"],
                        confidence=0.85,
                    ),
                ],
            )
            changes.append(scene_changes)

        metadata = {"description": "Bulk plan test"}

        plan = await manager.create_plan(
            "Bulk Plan", changes, metadata, test_async_session
        )

        assert plan.plan_metadata["total_changes"] == 100  # 2 changes per scene
        assert plan.plan_metadata["scene_count"] == 50

        # Verify all scenes marked as analyzed
        # Need to expire all objects to get fresh data after the commit in create_plan
        test_async_session.expire_all()
        result = await test_async_session.execute(
            select(Scene).where(Scene.analyzed.is_(True))
        )
        analyzed_scenes = result.scalars().all()
        assert len(analyzed_scenes) == 50

    @pytest.mark.asyncio
    async def test_apply_plan_with_many_changes(self, test_async_session):
        """Test applying a plan with many changes."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.update_scene = AsyncMock(return_value=True)
        stash_service.get_scene = AsyncMock(
            side_effect=[
                {"id": f"scene{i}", "title": f"Old Title {i}"} for i in range(20)
            ]
        )

        # Create a plan
        plan = AnalysisPlan(
            name="Bulk Apply Plan", status=PlanStatus.DRAFT, plan_metadata={}
        )
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add many changes
        for i in range(20):
            change = PlanChange(
                plan_id=plan.id,
                scene_id=f"scene{i}",
                field="title",
                action=ChangeAction.UPDATE,
                current_value=f"Old Title {i}",
                proposed_value=f"New Title {i}",
                confidence=0.9,
                status=ChangeStatus.APPROVED,
            )
            test_async_session.add(change)

        await test_async_session.commit()

        # Apply the plan
        result = await manager.apply_plan(plan.id, test_async_session, stash_service)

        assert result.total_changes == 20
        assert result.applied_changes == 20
        assert result.failed_changes == 0
        assert stash_service.update_scene.call_count == 20

    @pytest.mark.asyncio
    async def test_prepare_update_data_unknown_field(self, test_async_session):
        """Test prepare update data with unknown field."""
        manager = PlanManager()

        stash_service = Mock(spec=StashService)
        scene = {"id": "scene1"}

        change = PlanChange(
            plan_id=1,
            scene_id="scene1",
            field="unknown_field",
            action=ChangeAction.UPDATE,
            proposed_value="some value",
            confidence=0.9,
        )

        update_data = await manager._prepare_update_data(change, scene, stash_service)

        assert update_data == {}

    @pytest.mark.asyncio
    async def test_map_action_set_action(self, test_async_session):
        """Test mapping SET action."""
        manager = PlanManager()

        assert manager._map_action("set") == ChangeAction.SET
        assert manager._map_action("SET") == ChangeAction.SET

    @pytest.mark.asyncio
    async def test_delete_plan_not_found(self, test_async_session):
        """Test deleting a non-existent plan."""
        manager = PlanManager()

        result = await manager.delete_plan(99999, test_async_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_plan_statistics_empty_plan(self, test_async_session):
        """Test getting statistics for a plan with no changes."""
        manager = PlanManager()

        # Create a plan with no changes
        plan = AnalysisPlan(
            name="Empty Plan", status=PlanStatus.DRAFT, plan_metadata={}
        )
        test_async_session.add(plan)
        await test_async_session.commit()

        stats = await manager.get_plan_statistics(plan.id, test_async_session)

        assert stats["total_changes"] == 0
        assert stats["scenes_affected"] == 0
        assert stats["changes_by_action"] == {}
        assert stats["changes_by_field"] == {}
        assert stats["average_confidence"] == 0

    @pytest.mark.asyncio
    async def test_get_plan_statistics_non_existent(self, test_async_session):
        """Test getting statistics for non-existent plan."""
        manager = PlanManager()

        stats = await manager.get_plan_statistics(99999, test_async_session)

        assert stats == {}

    @pytest.mark.asyncio
    async def test_apply_plan_mixed_field_types(self, test_async_session):
        """Test applying a plan with mixed field types."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.update_scene = AsyncMock(return_value=True)
        stash_service.get_scene = AsyncMock(
            return_value={
                "id": "scene1",
                "title": "Old Title",
                "rating": 3,
                "details": "Old details",
            }
        )

        # Create a plan
        plan = AnalysisPlan(
            name="Mixed Fields Plan", status=PlanStatus.DRAFT, plan_metadata={}
        )
        test_async_session.add(plan)
        await test_async_session.flush()

        # Add changes with different field types
        changes = [
            PlanChange(
                plan_id=plan.id,
                scene_id="scene1",
                field="title",
                action=ChangeAction.UPDATE,
                current_value="Old Title",
                proposed_value="New Title",
                confidence=0.9,
                status=ChangeStatus.APPROVED,
            ),
            PlanChange(
                plan_id=plan.id,
                scene_id="scene1",
                field="rating",
                action=ChangeAction.UPDATE,
                current_value=3,
                proposed_value=5,
                confidence=0.85,
                status=ChangeStatus.APPROVED,
            ),
            PlanChange(
                plan_id=plan.id,
                scene_id="scene1",
                field="details",
                action=ChangeAction.UPDATE,
                current_value="Old details",
                proposed_value="New detailed description",
                confidence=0.8,
                status=ChangeStatus.APPROVED,
            ),
        ]

        test_async_session.add_all(changes)
        await test_async_session.commit()

        # Apply the plan
        result = await manager.apply_plan(plan.id, test_async_session, stash_service)

        assert result.total_changes == 3
        assert result.applied_changes == 3
        assert result.failed_changes == 0

        # Verify the correct update data was sent
        expected_calls = [
            call("scene1", {"title": "New Title"}),
            call("scene1", {"rating": 5}),
            call("scene1", {"details": "New detailed description"}),
        ]
        stash_service.update_scene.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    async def test_serialize_value_edge_cases(self, test_async_session):
        """Test value serialization with edge cases."""
        manager = PlanManager()

        # Test with custom object (should convert to string)
        class CustomObject:
            def __str__(self):
                return "custom_object_string"

        custom_obj = CustomObject()
        assert manager._serialize_value(custom_obj) == "custom_object_string"

        # Test with nested structures
        nested = {"a": [1, 2, {"b": 3}]}
        assert manager._serialize_value(nested) == {"a": [1, 2, {"b": 3}]}

        # Test with float
        assert manager._serialize_value(3.14) == 3.14

    @pytest.mark.asyncio
    async def test_add_performers_with_duplicates(self, test_async_session):
        """Test adding performers when some already exist."""
        manager = PlanManager()

        # Create mock stash service
        stash_service = Mock(spec=StashService)
        stash_service.find_performer = AsyncMock(
            side_effect=[{"id": "perf1"}, {"id": "perf2"}]
        )

        current_ids = ["perf1", "perf3"]
        new_performers = ["Performer 1", "Performer 2"]

        result_ids = await manager._add_performers(
            new_performers, current_ids, stash_service
        )

        # Should not duplicate perf1
        assert result_ids == ["perf1", "perf3", "perf2"]

    @pytest.mark.asyncio
    async def test_remove_performers_case_insensitive(self, test_async_session):
        """Test removing performers with case-insensitive matching."""
        manager = PlanManager()

        current_ids = ["perf1", "perf2", "perf3"]
        current_performers = [
            {"id": "perf1", "name": "John Doe"},
            {"id": "perf2", "name": "Jane Smith"},
            {"id": "perf3", "name": "Bob Johnson"},
        ]

        # Test case-insensitive removal
        remaining_ids = manager._remove_performers(
            ["JANE SMITH", {"name": "bob johnson"}], current_ids, current_performers
        )

        assert remaining_ids == ["perf1"]
