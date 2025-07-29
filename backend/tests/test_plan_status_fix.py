"""Test the plan status fix for completed jobs with no changes."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.job import JobStatus
from app.services.analysis.analysis_service import AnalysisService
from app.services.analysis.models import AnalysisOptions, SceneChanges


class TestPlanStatusFix:
    """Test fixes for plan status issues when jobs complete."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock()
        openai_client.model = "gpt-4o-mini"

        stash_service = Mock()
        settings = Mock()
        settings.analysis = Mock(batch_size=10, max_concurrent=1)

        service = AnalysisService(openai_client, stash_service, settings)
        service.plan_manager = Mock()
        service.plan_manager.finalize_plan = AsyncMock()
        service._update_job_progress = AsyncMock()

        return service

    @pytest.mark.asyncio
    async def test_pending_plan_finalized_when_no_changes(self, mock_service):
        """Test that PENDING plans are finalized as APPLIED when no changes found."""
        # Setup: Existing plan in PENDING status
        existing_plan = Mock(spec=AnalysisPlan)
        existing_plan.id = 123
        existing_plan.status = PlanStatus.PENDING
        existing_plan.add_metadata = Mock()
        existing_plan.get_metadata = Mock(return_value=5)  # 5 scenes analyzed

        mock_service.plan_manager.get_plan = AsyncMock(return_value=existing_plan)
        mock_service._current_plan_id = 123

        # Mock database
        db = Mock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()

        # Mock empty changes (no changes found)
        all_changes = [
            SceneChanges(
                scene_id=f"scene{i}",
                scene_title=f"Scene {i}",
                scene_path=f"/path/{i}",
                changes=[],
            )
            for i in range(5)
        ]

        # Execute finalization
        await mock_service._finalize_analysis(
            all_changes=all_changes,
            scenes=[Mock(id=f"scene{i}") for i in range(5)],
            processing_time=30.5,
            db=db,
            job_id="test-job-123",
            options=AnalysisOptions(),
        )

        # Verify the plan was properly finalized
        assert (
            existing_plan.status == PlanStatus.APPLIED
        ), f"Expected APPLIED status, got {existing_plan.status}"

        # Check metadata was updated
        metadata_calls = {
            call[0][0]: call[0][1] for call in existing_plan.add_metadata.call_args_list
        }
        assert metadata_calls.get("total_changes") == 0
        assert metadata_calls.get("reason") == "No changes detected"
        assert "completed_at" in metadata_calls

        # Verify job was updated as completed
        mock_service._update_job_progress.assert_called_with(
            "test-job-123",
            100,
            "Analysis complete - no changes found",
            JobStatus.COMPLETED,
        )

        # Verify database was committed
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_plan_with_changes_uses_normal_finalization(self, mock_service):
        """Test that plans with changes use the normal finalization flow."""
        # Setup
        plan_with_changes = Mock(spec=AnalysisPlan)
        plan_with_changes.id = 124
        plan_with_changes.status = PlanStatus.PENDING
        plan_with_changes.get_metadata = Mock(return_value=2)

        mock_service.plan_manager.get_plan = AsyncMock(return_value=plan_with_changes)
        mock_service.plan_manager.finalize_plan = AsyncMock()
        mock_service._current_plan_id = 124

        db = Mock()
        db.commit = AsyncMock()

        # Mock changes found
        all_changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/1",
                changes=[Mock()],  # Has changes
            ),
            SceneChanges(
                scene_id="scene2",
                scene_title="Scene 2",
                scene_path="/path/2",
                changes=[],  # No changes
            ),
        ]

        # Execute finalization
        await mock_service._finalize_analysis(
            all_changes=all_changes,
            scenes=[Mock(id="scene1"), Mock(id="scene2")],
            processing_time=20.0,
            db=db,
            job_id="test-job-124",
            options=AnalysisOptions(),
        )

        # Verify finalize_plan was called (normal flow)
        mock_service.plan_manager.finalize_plan.assert_called_once()
        call_args = mock_service.plan_manager.finalize_plan.call_args
        assert call_args[0][0] == 124  # plan_id
        assert call_args[0][1] == db  # database session

        # The plan should not have been modified directly
        assert plan_with_changes.status == PlanStatus.PENDING

    @pytest.mark.asyncio
    async def test_no_plan_created_when_no_changes(self, mock_service):
        """Test that no plan is created when there are no changes to begin with."""
        # Setup - no existing plan
        mock_service._current_plan_id = None
        mock_service._plan_metadata = {"test": "metadata"}  # Initialize the metadata
        mock_service._current_plan_name = "Test Plan"
        mock_service.plan_manager.get_plan = AsyncMock(return_value=None)
        mock_service._handle_no_changes = AsyncMock()

        # Create a mock plan to return
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.status = PlanStatus.APPLIED
        mock_service._handle_no_changes.return_value = mock_plan

        db = Mock()

        # Mock empty changes
        all_changes = []

        # Execute finalization
        result = await mock_service._finalize_analysis(
            all_changes=all_changes,
            scenes=[],
            processing_time=0.1,
            db=db,
            job_id="test-job-125",
            options=AnalysisOptions(),
        )

        # Verify _handle_no_changes was called
        mock_service._handle_no_changes.assert_called_once()

        # Verify result is the mock plan
        assert result == mock_plan
        assert result.status == PlanStatus.APPLIED
