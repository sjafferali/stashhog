"""Test handling of missing/deleted scenes in plan application."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.plan_change import ChangeAction, ChangeStatus
from app.services.analysis.models import ApplyResult
from app.services.analysis.plan_manager import PlanManager


@pytest.mark.asyncio
async def test_apply_single_change_with_missing_scene():
    """Test that missing scenes are handled gracefully and marked as applied."""
    plan_manager = PlanManager()

    # Mock database session
    db_mock = AsyncMock()

    # Mock stash service that returns None for missing scene
    stash_service_mock = AsyncMock()
    stash_service_mock.get_scene.return_value = None

    # Create a mock change
    change = MagicMock()
    change.scene_id = 30960
    change.field = "tags"
    change.action = ChangeAction.ADD
    change.proposed_value = ["test_tag"]

    # Apply the change - should return "skipped" and mark as APPLIED
    result = await plan_manager.apply_single_change(change, db_mock, stash_service_mock)

    assert result == "skipped"
    assert change.status == ChangeStatus.APPLIED  # Verify change is marked as applied
    assert change.applied_at is not None  # Verify applied_at is set
    stash_service_mock.get_scene.assert_called_once_with("30960")
    db_mock.flush.assert_called()  # Verify database flush was called


@pytest.mark.asyncio
async def test_process_plan_changes_with_missing_scenes():
    """Test that plan processing handles missing scenes correctly."""
    plan_manager = PlanManager()

    # Mock database session
    db_mock = AsyncMock()

    # Mock stash service
    stash_service_mock = AsyncMock()
    # First scene exists, second doesn't, third exists
    stash_service_mock.get_scene.side_effect = [
        {"id": "1", "tags": []},  # Scene 1 exists
        None,  # Scene 2 is missing
        {"id": "3", "tags": []},  # Scene 3 exists
    ]
    stash_service_mock.find_tag.return_value = {"id": "tag1", "name": "test_tag"}
    stash_service_mock.update_scene.return_value = True

    # Create mock changes
    changes = [
        MagicMock(
            id=1,
            scene_id=1,
            field="tags",
            action=ChangeAction.ADD,
            proposed_value=["test_tag"],
            status=ChangeStatus.APPROVED,
        ),
        MagicMock(
            id=2,
            scene_id=2,
            field="tags",
            action=ChangeAction.ADD,
            proposed_value=["test_tag"],
            status=ChangeStatus.APPROVED,
        ),
        MagicMock(
            id=3,
            scene_id=3,
            field="tags",
            action=ChangeAction.ADD,
            proposed_value=["test_tag"],
            status=ChangeStatus.APPROVED,
        ),
    ]

    # Process changes
    result = await plan_manager._process_plan_changes(
        changes=changes,
        apply_filters={"tags": True},
        db=db_mock,
        stash_service=stash_service_mock,
        change_ids=None,
        progress_callback=None,
    )

    # Verify results
    assert result["total_changes"] == 3
    assert result["applied_changes"] == 2  # Two scenes were updated
    assert result["skipped_changes"] == 1  # One scene was missing
    assert result["failed_changes"] == 0  # No actual failures
    assert len(result["modified_scene_ids"]) == 2  # Only 2 scenes modified


@pytest.mark.asyncio
async def test_apply_plan_with_all_scenes_missing():
    """Test that a plan with all missing scenes doesn't fail."""
    plan_manager = PlanManager()

    # Mock database session with plan and changes
    db_mock = AsyncMock()

    # Mock plan
    plan_mock = MagicMock()
    plan_mock.id = 1
    plan_mock.status = "DRAFT"
    plan_mock.can_be_applied.return_value = True
    plan_mock.add_metadata = MagicMock()

    # Mock stash service - all scenes are missing
    stash_service_mock = AsyncMock()
    stash_service_mock.get_scene.return_value = None

    with patch.object(plan_manager, "get_plan", return_value=plan_mock):
        with patch.object(
            plan_manager,
            "_get_plan_changes",
            return_value=[
                MagicMock(
                    id=1,
                    scene_id=30960,
                    field="tags",
                    action=ChangeAction.ADD,
                    proposed_value=["test_tag"],
                    status=ChangeStatus.APPROVED,
                ),
                MagicMock(
                    id=2,
                    scene_id=30961,
                    field="tags",
                    action=ChangeAction.ADD,
                    proposed_value=["test_tag"],
                    status=ChangeStatus.APPROVED,
                ),
            ],
        ):
            with patch.object(
                plan_manager, "_update_plan_status_async", return_value=None
            ):
                result = await plan_manager.apply_plan(
                    plan_id=1, db=db_mock, stash_service=stash_service_mock
                )

    # Verify the result
    assert isinstance(result, ApplyResult)
    assert result.plan_id == 1
    assert result.applied_changes == 0
    assert result.skipped_changes == 2  # Both scenes were skipped
    assert result.failed_changes == 0  # No failures, just missing scenes
    assert result.total_changes == 2


@pytest.mark.asyncio
async def test_daemon_skips_failed_plans():
    """Test that the daemon doesn't retry failed plans."""
    from app.daemons.auto_plan_applier_daemon import AutoPlanApplierDaemon
    from app.models import PlanStatus

    # Create daemon instance with valid UUID
    daemon = AutoPlanApplierDaemon(
        daemon_id=str(uuid.uuid4()), config={"auto_approve_all_changes": False}
    )

    # Mock database-related methods to prevent actual database interaction
    daemon.log = AsyncMock()
    daemon.update_heartbeat = AsyncMock()
    daemon.is_running = True

    # Mock on_start to prevent database access during initialization
    daemon.on_start = AsyncMock()

    # Initialize daemon state without calling on_start() to avoid any database interaction
    daemon._monitored_jobs = set()
    daemon._job_to_plan_mapping = {}
    daemon._failed_plans = {123}  # Add plan 123 to failed list
    daemon._processed_plans = {456}  # Add plan 456 to processed list

    # Mock database session
    db_mock = AsyncMock()

    # Create mock plans
    plans = [
        MagicMock(id=123, name="Failed Plan", status=PlanStatus.DRAFT),
        MagicMock(id=456, name="Processed Plan", status=PlanStatus.DRAFT),
        MagicMock(id=789, name="New Plan", status=PlanStatus.DRAFT),
    ]

    # Mock the database query - patch at the module level where it's imported
    with patch(
        "app.daemons.auto_plan_applier_daemon.AsyncSessionLocal"
    ) as mock_session:
        mock_session.return_value.__aenter__.return_value = db_mock

        # Create mock result chain
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = plans
        mock_result.scalars.return_value = mock_scalars

        db_mock.execute.return_value = mock_result

        # Mock _should_process_plan to return True
        with patch.object(daemon, "_should_process_plan", return_value=True):
            # Mock _create_and_wait_for_job with a valid UUID
            with patch.object(
                daemon, "_create_and_wait_for_job", return_value=str(uuid.uuid4())
            ) as mock_create:
                # Process plans with full config
                processed = await daemon._process_plans(
                    {"plan_prefix_filter": [], "auto_approve_all_changes": False}
                )

                # Verify only the new plan (789) was processed
                assert processed == 1
                mock_create.assert_called_once()
                # Get the first argument of the call
                call_args = mock_create.call_args[0]
                assert call_args[0] == 789  # Only plan 789 should be processed


@pytest.mark.asyncio
async def test_plan_status_updated_when_all_changes_skipped():
    """Test that plan status is correctly set to APPLIED when all changes are skipped."""

    from app.models import AnalysisPlan, PlanStatus

    plan_manager = PlanManager()

    # Mock database session
    db_mock = AsyncMock()

    # Create a mock plan
    plan = MagicMock(spec=AnalysisPlan)
    plan.id = 1
    plan.status = PlanStatus.REVIEWING
    plan.applied_at = None

    # Mock the count queries to simulate all changes being applied (due to skips)
    db_mock.execute.side_effect = [
        MagicMock(scalar=lambda: 2),  # Total changes
        MagicMock(scalar=lambda: 2),  # Applied changes (including skipped)
        MagicMock(scalar=lambda: 0),  # Approved changes (none left)
        MagicMock(scalar=lambda: 0),  # Rejected changes
        MagicMock(scalar=lambda: 0),  # Pending changes
    ]

    # Call the update method
    await plan_manager._update_plan_status_async(plan, db_mock)

    # Verify the plan was marked as APPLIED
    assert plan.status == PlanStatus.APPLIED
    assert plan.applied_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
