"""Tests for analysis API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import (
    get_analysis_service,
    get_current_user,
    get_db,
    get_job_service,
    get_openai_client,
    get_settings,
    get_stash_service,
)
from app.main import app
from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.plan_change import ChangeAction, ChangeStatus, PlanChange


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"sub": "test_user", "email": "test@example.com"}


@pytest.fixture
def client(mock_db, mock_user):
    """Test client with mocked dependencies."""
    # Mock all required dependencies
    from app.core.config import Settings
    from app.services.analysis.analysis_service import AnalysisService
    from app.services.job_service import JobService
    from app.services.stash_service import StashService

    # Create mock services
    mock_settings = Settings()
    mock_stash_service = Mock(spec=StashService)
    mock_openai_client = None  # Can be None for tests
    mock_analysis_service = Mock(spec=AnalysisService)
    mock_job_service = Mock(spec=JobService)

    # Override all dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_service
    app.dependency_overrides[get_openai_client] = lambda: mock_openai_client
    app.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service
    app.dependency_overrides[get_job_service] = lambda: mock_job_service

    with TestClient(app) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_plan():
    """Create a mock analysis plan."""
    plan = Mock(spec=AnalysisPlan)
    plan.id = str(uuid4())
    plan.name = "Test Analysis Plan"
    plan.description = "Plan for testing"
    plan.scene_count = 10
    plan.change_count = 5
    plan.status = "draft"
    plan.created_at = datetime.utcnow()
    plan.updated_at = datetime.utcnow()
    plan.created_by = "test_user"
    plan.applied_at = None
    plan.applied_by = None
    plan.changes = []
    plan.to_dict = Mock(
        return_value={
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "scene_count": plan.scene_count,
            "change_count": plan.change_count,
            "status": plan.status,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "created_by": plan.created_by,
            "applied_at": None,
            "applied_by": None,
            "changes": [],
        }
    )
    return plan


@pytest.fixture
def mock_change():
    """Create a mock plan change."""
    change = Mock(spec=PlanChange)
    change.id = str(uuid4())
    change.plan_id = str(uuid4())
    change.scene_id = str(uuid4())
    change.change_type = ChangeAction.UPDATE
    change.field_name = "title"
    change.old_value = "Old Title"
    change.new_value = "New Title"
    change.confidence = 0.95
    change.approved = True
    change.applied = False
    change.to_dict = Mock(
        return_value={
            "id": change.id,
            "plan_id": change.plan_id,
            "scene_id": change.scene_id,
            "change_type": change.change_type.value,
            "field_name": change.field_name,
            "old_value": change.old_value,
            "new_value": change.new_value,
            "confidence": change.confidence,
            "approved": change.approved,
            "applied": change.applied,
        }
    )
    return change


class TestAnalysisRoutes:
    """Test analysis API routes."""

    def test_list_plans(self, client, mock_db):
        """Test listing analysis plans."""
        # Mock the count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock the plans query
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_plans_result = Mock()
        mock_plans_result.scalars.return_value = mock_scalars

        # Set up execute to return different results for count and list queries
        mock_db.execute.side_effect = [mock_count_result, mock_plans_result]

        response = client.get("/api/analysis/plans")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        # With empty test database
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_plan_not_found(self, client, mock_db):
        """Test getting a plan that doesn't exist."""
        # Mock the database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/analysis/plans/999999")

        assert response.status_code == 404

    def test_get_plan_detail(self, client, mock_db):
        """Test getting detailed plan with changes (serves as preview)."""
        plan_id = 1

        # Mock plan
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = plan_id
        mock_plan.name = "Test Analysis Plan"
        mock_plan.status = PlanStatus.DRAFT
        mock_plan.created_at = datetime.utcnow()
        mock_plan.plan_metadata = {"model": "gpt-4"}
        mock_plan.job_id = None  # Add job_id attribute

        # Mock scene
        mock_scene = Mock()
        mock_scene.id = "scene123"
        mock_scene.title = "Test Scene"
        mock_scene.files = []
        mock_scene.get_primary_file = Mock(return_value=None)

        # Mock changes
        mock_change1 = Mock()
        mock_change1.id = 1
        mock_change1.field = "title"
        mock_change1.action = "update"
        mock_change1.current_value = "Old Title"
        mock_change1.proposed_value = "New Title"
        mock_change1.confidence = 0.95
        # Create a proper mock for status enum - use spec to prevent auto-creation of attributes
        from app.models.plan_change import ChangeStatus

        mock_change1.status = ChangeStatus.PENDING
        mock_change1.applied = False

        mock_change2 = Mock()
        mock_change2.id = 2
        mock_change2.field = "details"
        mock_change2.action = "set"
        mock_change2.current_value = None
        mock_change2.proposed_value = "New details"
        mock_change2.confidence = 0.85
        mock_change2.status = ChangeStatus.APPROVED
        mock_change2.applied = False

        # Mock query results
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan

        mock_changes_result = Mock()
        mock_changes_result.all.return_value = [
            (mock_change1, mock_scene),
            (mock_change2, mock_scene),
        ]

        # Mock count result for total changes
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2

        # Try a simpler approach - since we know the order of calls,
        # let's use a list of return values

        # Create mock results for each query in order
        approved_result = Mock()
        approved_result.scalar_one = Mock(return_value=1)  # approved count

        rejected_result = Mock()
        rejected_result.scalar_one = Mock(return_value=0)  # rejected count

        # Set up the mock to return different results for each call
        # The order should be:
        # 1. Get plan by ID
        # 2. Get changes for plan
        # 3. Get total count
        # 4. Get approved count
        # 5. Get rejected count
        mock_db.execute.side_effect = [
            mock_plan_result,  # plan query
            mock_changes_result,  # changes query
            mock_count_result,  # total count
            approved_result,  # approved count
            rejected_result,  # rejected count
        ]

        response = client.get(f"/api/analysis/plans/{plan_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == plan_id
        assert data["name"] == "Test Analysis Plan"
        assert data["status"] == "DRAFT"
        assert data["total_scenes"] == 1
        assert data["total_changes"] == 2
        assert "scenes" in data
        assert len(data["scenes"]) == 1

        scene_data = data["scenes"][0]
        assert scene_data["scene_id"] == "scene123"
        assert scene_data["scene_title"] == "Test Scene"
        assert len(scene_data["changes"]) == 2

        # Verify changes
        change1 = scene_data["changes"][0]
        assert change1["field"] == "title"
        assert change1["current_value"] == "Old Title"
        assert change1["proposed_value"] == "New Title"
        assert change1["confidence"] == 0.95
        assert change1["status"] == "pending"

        change2 = scene_data["changes"][1]
        assert change2["field"] == "details"
        assert change2["proposed_value"] == "New details"
        assert change2["status"] == "approved"

    def test_list_plans_with_pagination(self, client, mock_db):
        """Test listing plans with pagination and filtering."""
        # Mock plans
        plans = []
        for i in range(3):
            plan = Mock(spec=AnalysisPlan)
            plan.id = i + 1
            plan.name = f"Plan {i + 1}"
            plan.status = PlanStatus.DRAFT if i < 2 else PlanStatus.APPLIED
            plan.created_at = datetime.utcnow()
            plan.plan_metadata = {}
            # Ensure any list attributes that might be accessed are set
            plan.changes = []
            plan.job_id = None  # Add job_id attribute
            plans.append(plan)

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 2  # Only 2 draft plans

        # Mock plans query
        mock_scalars = Mock()
        mock_scalars.all.return_value = plans[:2]  # Return only draft plans
        mock_plans_result = Mock()
        mock_plans_result.scalars.return_value = mock_scalars

        # Track query execution order
        execution_order = []

        async def async_execute(query):
            execution_order.append(query)

            # First query is always the count query for total plans
            if len(execution_order) == 1:
                return mock_count_result
            # Second query is the plans query
            elif len(execution_order) == 2:
                return mock_plans_result
            # Subsequent queries alternate between change count and scene count for each plan
            else:
                result = Mock()
                # Odd queries (3, 5, 7...) are change counts
                if len(execution_order) % 2 == 1:
                    result.scalar_one.return_value = 5
                # Even queries (4, 6, 8...) are scene counts
                else:
                    result.scalar_one.return_value = 2
                return result

        mock_db.execute = async_execute

        response = client.get("/api/analysis/plans?status=draft&page=1&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert len(data["items"]) == 2

        # Verify plan data
        plan1 = data["items"][0]
        assert plan1["name"] == "Plan 1"
        assert plan1["status"] == "DRAFT"
        assert plan1["total_scenes"] == 2
        assert plan1["total_changes"] == 5

    def test_create_analysis_plan(self, client, mock_db):
        """Test creating a new analysis plan."""
        # Mock the database query for getting scene IDs
        mock_execute_result = Mock()
        mock_execute_result.__iter__ = Mock(
            return_value=iter([])
        )  # No scene filtering needed

        async def async_execute(query):
            return mock_execute_result

        mock_db.execute = async_execute

        # Get the mocked services from the overrides
        mock_job_service = app.dependency_overrides[get_job_service]()
        mock_job = Mock()
        mock_job.id = "job123"
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        mock_analysis_service = app.dependency_overrides[get_analysis_service]()
        mock_analysis_service.analyze_scenes = (
            AsyncMock()
        )  # Mock the analyze_scenes method

        request_data = {
            "scene_ids": ["scene1", "scene2", "scene3"],
            "options": {
                "detect_performers": True,
                "detect_tags": True,
                "detect_details": True,  # Changed from generate_details
                "detect_studios": True,
                "detect_video_tags": False,
                "confidence_threshold": 0.7,
            },
            "plan_name": "New Analysis",
        }

        response = client.post("/api/analysis/generate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job123"
        assert data["status"] == "queued"
        mock_job_service.create_job.assert_called_once()

    def test_update_plan(self, client, mock_db, mock_plan):
        """Test updating an analysis plan change."""
        mock_change = Mock(spec=PlanChange)
        mock_change.id = 1
        mock_change.applied = False
        mock_change.field = "title"
        mock_change.action = "update"
        mock_change.current_value = "Old Value"
        mock_change.proposed_value = "New Value"
        mock_change.confidence = 0.9

        # Mock async query execution
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = mock_change

        # Create async context manager for execute
        async def async_execute(*args, **kwargs):
            return mock_execute_result

        mock_db.execute = async_execute
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # The endpoint expects proposed_value as a direct value in the body
        response = client.patch("/api/analysis/changes/1", json="Updated Value")

        assert response.status_code == 200
        data = response.json()
        assert data["proposed_value"] == "Updated Value"

    def test_delete_plan(self, client):
        """Test deleting an analysis plan - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        response = client.delete("/api/analysis/plans/1")

        assert response.status_code == 405  # Method not allowed

    def test_approve_change(self, client):
        """Test approving a plan change - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        response = client.post("/api/analysis/changes/1/approve")

        assert response.status_code == 404

    def test_reject_change(self, client):
        """Test rejecting a plan change - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        response = client.post("/api/analysis/changes/1/reject")

        assert response.status_code == 404

    def test_apply_plan(self, client, mock_db, mock_plan):
        """Test applying an analysis plan."""
        mock_plan.status = "draft"

        # Mock async query execution
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = mock_plan

        # Create async context manager for execute
        async def async_execute(*args, **kwargs):
            return mock_execute_result

        mock_db.execute = async_execute

        # Get the mocked services from the overrides
        mock_job_service = app.dependency_overrides[get_job_service]()
        mock_job = Mock()
        mock_job.id = "job456"
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        mock_analysis_service = app.dependency_overrides[get_analysis_service]()
        mock_analysis_service.apply_plan = AsyncMock()

        response = client.post("/api/analysis/plans/1/apply", json={"background": True})

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job456"
        assert data["status"] == "queued"
        mock_job_service.create_job.assert_called_once()

    def test_get_plan_preview(self, client):
        """Test getting plan preview - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        response = client.get("/api/analysis/plans/1/preview")

        assert response.status_code == 404

    def test_bulk_approve_changes(self, client):
        """Test bulk approving changes - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        change_ids = [str(uuid4()) for _ in range(3)]
        response = client.post(
            "/api/analysis/changes/bulk-approve", json={"change_ids": change_ids}
        )

        assert response.status_code == 405  # Method not allowed

    def test_get_analysis_stats(self, client, mock_db):
        """Test getting analysis statistics."""
        # Mock database responses for stats queries
        mock_result = Mock()
        mock_result.scalar_one = Mock(return_value=10)
        mock_db.execute.return_value = mock_result

        response = client.get("/api/analysis/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_scenes" in data
        assert "analyzed_scenes" in data
        assert "total_plans" in data
        assert "pending_plans" in data
        assert "pending_analysis" in data

    def test_analyze_single_scene(self, client):
        """Test analyzing a single scene - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        scene_id = str(uuid4())
        response = client.post(f"/api/analysis/scenes/{scene_id}/analyze")

        assert response.status_code == 404

    def test_bulk_update_changes_accept_all(self, client, mock_db):
        """Test bulk accepting all changes in a plan."""
        plan_id = 1

        # Mock the plan query
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.name = "Test Plan"
        mock_plan.status = "draft"

        # Mock changes to be updated
        mock_changes = []
        for i in range(3):
            change = Mock()
            change.id = i + 1
            change.accepted = False
            change.rejected = False
            change.applied = False
            mock_changes.append(change)

        # Setup mock execution results
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan

        mock_changes_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_changes
        mock_changes_result.scalars.return_value = mock_scalars

        # Mock count results
        mock_count_result = Mock()
        mock_count_result.scalar_one.side_effect = [
            3,
            0,
            0,
            3,
            0,
        ]  # total, applied, rejected, accepted, pending

        async def async_execute(query):
            # Return different results based on query type
            if "analysis_plan" in str(query):
                return mock_plan_result
            elif "count" in str(query):
                return mock_count_result
            else:
                return mock_changes_result

        mock_db.execute = async_execute
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client.post(
            f"/api/analysis/plans/{plan_id}/bulk-update", json={"action": "accept_all"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept_all"
        assert data["updated_count"] == 3
        assert data["total_changes"] == 3
        assert data["pending_changes"] == 0

        # Verify changes were updated
        for change in mock_changes:
            assert change.status == ChangeStatus.APPROVED

    def test_bulk_update_changes_by_field(self, client, mock_db):
        """Test bulk accepting changes for a specific field."""
        plan_id = 1
        field_name = "title"

        # Mock the plan
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.name = "Test Plan"
        mock_plan.status = "draft"

        # Mock changes - some for title field, some for other fields
        mock_changes = []
        title_change = Mock()
        title_change.field = "title"
        title_change.accepted = False
        title_change.rejected = False
        title_change.applied = False
        mock_changes.append(title_change)

        # Setup mock execution
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan

        mock_changes_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_changes
        mock_changes_result.scalars.return_value = mock_scalars

        mock_count_result = Mock()
        mock_count_result.scalar_one.side_effect = [
            5,
            0,
            0,
            1,
            4,
        ]  # total, applied, rejected, accepted, pending

        async def async_execute(query):
            if "analysis_plan" in str(query):
                return mock_plan_result
            elif "count" in str(query):
                return mock_count_result
            else:
                return mock_changes_result

        mock_db.execute = async_execute
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client.post(
            f"/api/analysis/plans/{plan_id}/bulk-update",
            json={"action": "accept_by_field", "field": field_name},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept_by_field"
        assert data["updated_count"] == 1
        assert title_change.status == ChangeStatus.APPROVED

    def test_bulk_update_changes_by_confidence(self, client, mock_db):
        """Test bulk accepting changes above a confidence threshold."""
        plan_id = 1
        confidence_threshold = 0.8

        # Mock the plan
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.name = "Test Plan"
        mock_plan.status = "draft"

        # Mock changes with different confidence levels
        mock_changes = []
        high_conf_change = Mock()
        high_conf_change.confidence = 0.9
        high_conf_change.accepted = False
        high_conf_change.rejected = False
        high_conf_change.applied = False
        mock_changes.append(high_conf_change)

        # Setup mock execution
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan

        mock_changes_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_changes
        mock_changes_result.scalars.return_value = mock_scalars

        mock_count_result = Mock()
        mock_count_result.scalar_one.side_effect = [5, 0, 0, 1, 4]

        async def async_execute(query):
            if "analysis_plan" in str(query):
                return mock_plan_result
            elif "count" in str(query):
                return mock_count_result
            else:
                return mock_changes_result

        mock_db.execute = async_execute
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client.post(
            f"/api/analysis/plans/{plan_id}/bulk-update",
            json={
                "action": "accept_by_confidence",
                "confidence_threshold": confidence_threshold,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept_by_confidence"
        assert data["updated_count"] == 1
        assert high_conf_change.status == ChangeStatus.APPROVED

    def test_bulk_update_missing_params(self, client, mock_db):
        """Test bulk update with missing required parameters."""
        plan_id = 1

        # Mock the plan
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.name = "Test Plan"
        mock_plan.status = "draft"

        # Mock result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_plan

        # Setup mock execute as async function
        async def async_execute(query):
            return mock_result

        mock_db.execute = async_execute

        # Test missing field for field-based action
        response = client.post(
            f"/api/analysis/plans/{plan_id}/bulk-update",
            json={"action": "accept_by_field"},
        )
        assert response.status_code == 400
        assert "Field parameter is required" in response.json()["detail"]

        # Test missing confidence threshold
        response = client.post(
            f"/api/analysis/plans/{plan_id}/bulk-update",
            json={"action": "accept_by_confidence"},
        )
        assert response.status_code == 400
        assert "Confidence threshold is required" in response.json()["detail"]

    def test_bulk_update_plan_not_found(self, client, mock_db):
        """Test bulk update on non-existent plan."""
        plan_id = 999

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.post(
            f"/api/analysis/plans/{plan_id}/bulk-update", json={"action": "accept_all"}
        )

        assert response.status_code == 404
        assert f"Analysis plan {plan_id} not found" in response.json()["detail"]

    def test_generate_analysis_with_filters(self, client, mock_db):
        """Test generating analysis using scene filters."""
        # Mock scene IDs from filter query
        mock_scene_ids = ["scene1", "scene2", "scene3"]

        async def async_execute(query):
            # Return scene IDs for filter query
            result = Mock()
            result.__iter__ = Mock(return_value=iter([(id,) for id in mock_scene_ids]))
            return result

        mock_db.execute = async_execute

        # Get mocked services
        mock_job_service = app.dependency_overrides[get_job_service]()
        mock_job = Mock()
        mock_job.id = "job789"
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        request_data = {
            "filters": {"search": "test", "analyzed": False, "organized": True},
            "options": {
                "detect_performers": True,
                "detect_tags": True,
                "detect_details": False,
                "detect_studios": False,
                "detect_video_tags": False,
                "confidence_threshold": 0.7,
            },
            "plan_name": "Filtered Analysis",
        }

        response = client.post("/api/analysis/generate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job789"
        assert data["status"] == "queued"
        assert "3 scenes" in data["message"]

    def test_generate_analysis_sync_mode(self, client, mock_db):
        """Test generating analysis in synchronous mode."""
        scene_ids = ["scene1", "scene2"]

        # Mock empty result for filter query and count query
        mock_filter_result = Mock(__iter__=Mock(return_value=iter([])))
        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=5)

        # First call returns filter result, second call returns count
        mock_db.execute = AsyncMock(side_effect=[mock_filter_result, mock_count_result])

        # Get mocked analysis service
        mock_analysis_service = app.dependency_overrides[get_analysis_service]()

        # Create a mock plan that looks like a real AnalysisPlan object
        from app.models.analysis_plan import AnalysisPlan

        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = 123
        mock_plan.get_change_count = Mock(return_value=5)

        # The endpoint also needs to execute a count query for changes
        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=5)

        # Update the execute mock to handle the count query
        original_execute = mock_db.execute

        async def execute_with_count(query):
            # Check if this is a count query
            query_str = str(query)
            if "count" in query_str.lower() and "plan_change" in query_str.lower():
                return mock_count_result
            # Otherwise use the original side effect
            return await original_execute(query)

        mock_db.execute = AsyncMock(side_effect=execute_with_count)
        mock_analysis_service.analyze_scenes = AsyncMock(return_value=mock_plan)

        request_data = {
            "scene_ids": scene_ids,
            "options": {
                "detect_performers": True,
                "detect_tags": True,
                "detect_details": True,
                "detect_studios": True,
                "detect_video_tags": False,
                "confidence_threshold": 0.7,
            },
        }

        response = client.post(
            "/api/analysis/generate?background=false", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["plan_id"] == 123
        assert data["total_scenes"] == 2
        assert data["total_changes"] == 5

    def test_generate_analysis_no_scenes_error(self, client, mock_db):
        """Test error when no scenes match criteria."""

        # Mock empty scene IDs from filter
        async def async_execute(query):
            result = Mock()
            result.__iter__ = Mock(return_value=iter([]))
            return result

        mock_db.execute = async_execute

        request_data = {
            "filters": {"analyzed": True},  # No scenes match
            "options": {
                "detect_performers": True,
                "detect_tags": False,
                "detect_details": False,
                "detect_studios": False,
                "detect_video_tags": False,
                "confidence_threshold": 0.7,
            },
        }

        response = client.post("/api/analysis/generate", json=request_data)

        assert response.status_code == 400
        assert "No scenes found" in response.json()["detail"]

    def test_get_plan_costs(self, client, mock_db):
        """Test getting cost breakdown for a plan."""
        plan_id = 1

        # Mock plan with API usage metadata
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = plan_id
        mock_plan.name = "Test Plan"

        # Mock the get_metadata method
        api_usage = {
            "total_cost": 0.15,
            "total_tokens": 5000,
            "prompt_tokens": 3000,
            "completion_tokens": 2000,
            "cost_breakdown": {"prompt_cost": 0.09, "completion_cost": 0.06},
            "token_breakdown": {
                "scene_1": {"prompt": 1500, "completion": 1000},
                "scene_2": {"prompt": 1500, "completion": 1000},
            },
            "model": "gpt-4",
            "scenes_analyzed": 2,
            "average_cost_per_scene": 0.075,
        }
        mock_plan.get_metadata = Mock(return_value=api_usage)

        # Mock database get
        mock_db.get = AsyncMock(return_value=mock_plan)

        response = client.get(f"/api/analysis/plans/{plan_id}/costs")

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == plan_id
        assert data["total_cost"] == 0.15
        assert data["total_tokens"] == 5000
        assert data["prompt_tokens"] == 3000
        assert data["completion_tokens"] == 2000
        assert data["model"] == "gpt-4"
        assert data["scenes_analyzed"] == 2
        assert data["average_cost_per_scene"] == 0.075
        assert data["currency"] == "USD"
        assert "cost_breakdown" in data
        assert "token_breakdown" in data

    def test_get_plan_costs_no_data(self, client, mock_db):
        """Test getting costs for a plan with no API usage data."""
        plan_id = 1

        # Mock plan without API usage metadata
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = plan_id
        mock_plan.get_metadata = Mock(return_value={})

        mock_db.get = AsyncMock(return_value=mock_plan)

        response = client.get(f"/api/analysis/plans/{plan_id}/costs")

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == plan_id
        assert data["total_cost"] == 0.0
        assert data["total_tokens"] == 0
        assert data["model"] is None
        assert data["currency"] == "USD"
        assert "No API usage data available" in data["message"]

    def test_get_plan_costs_not_found(self, client, mock_db):
        """Test getting costs for non-existent plan."""
        plan_id = 999

        mock_db.get = AsyncMock(return_value=None)

        response = client.get(f"/api/analysis/plans/{plan_id}/costs")

        assert response.status_code == 404
        assert "Plan not found" in response.json()["detail"]

    def test_get_available_models(self, client):
        """Test getting available OpenAI models."""
        response = client.get("/api/analysis/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "categories" in data
        assert "default" in data
        assert "recommended" in data

        # Verify structure of models
        assert isinstance(data["models"], dict)
        assert isinstance(data["categories"], dict)
        assert isinstance(data["default"], str)
        assert isinstance(data["recommended"], dict)

    def test_get_scene_analysis_results(self, client, mock_db):
        """Test getting analysis results for a specific scene."""
        scene_id = "scene123"

        # Mock plan
        mock_plan = Mock()
        mock_plan.id = 1
        mock_plan.name = "Test Plan"
        mock_plan.created_at = datetime.utcnow()
        mock_plan.plan_metadata = {
            "ai_model": "gpt-4",
            "prompt_template": "Analyze this scene",
            "raw_response": "AI response text",
            "processing_time": 2.5,
        }

        # Mock changes
        mock_changes = []
        change1 = Mock()
        change1.field = "title"
        change1.action = "update"
        change1.proposed_value = "New Title"
        change1.confidence = 0.95
        mock_changes.append((change1, mock_plan))

        change2 = Mock()
        change2.field = "performers"
        change2.action = "add"
        change2.proposed_value = {"name": "John Doe"}
        change2.confidence = 0.85
        mock_changes.append((change2, mock_plan))

        # Mock query result
        mock_result = Mock()
        mock_result.all.return_value = mock_changes
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get(f"/api/analysis/scenes/{scene_id}/results")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1  # One plan

        result = data[0]
        assert result["scene_id"] == scene_id
        assert result["plan"]["id"] == 1
        assert result["plan"]["name"] == "Test Plan"
        assert result["model_used"] == "gpt-4"
        assert result["prompt_used"] == "Analyze this scene"
        assert result["raw_response"] == "AI response text"
        assert result["processing_time"] == 2.5
        assert "extracted_data" in result
        assert "confidence_scores" in result
        assert result["extracted_data"]["title"] == "New Title"
        assert result["extracted_data"]["performers"] == ["John Doe"]
        assert result["confidence_scores"]["title"] == 0.95
        assert result["confidence_scores"]["performers"] == 0.85

    def test_get_scene_analysis_results_empty(self, client, mock_db):
        """Test getting analysis results for scene with no results."""
        scene_id = "scene456"

        # Mock empty result
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get(f"/api/analysis/scenes/{scene_id}/results")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_update_change_status(self, client, mock_db):
        """Test updating the acceptance/rejection status of a change."""
        change_id = 1

        # Mock change
        mock_change = Mock()
        mock_change.id = change_id
        mock_change.plan_id = 1
        mock_change.field = "title"
        mock_change.action = "update"
        mock_change.current_value = "Old Title"
        mock_change.proposed_value = "New Title"
        mock_change.confidence = 0.9
        mock_change.applied = False
        mock_change.accepted = False
        mock_change.rejected = False

        # Mock plan
        mock_plan = Mock()
        mock_plan.status = PlanStatus.DRAFT

        # Setup mock execution
        mock_change_result = Mock()
        mock_change_result.scalar_one_or_none.return_value = mock_change

        mock_plan_result = Mock()
        mock_plan_result.scalar_one.return_value = mock_plan

        # Track which queries have been called
        query_count = 0

        async def async_execute(query):
            nonlocal query_count
            query_str = str(query)

            # First query is to get the change
            if query_count == 0 and "plan_change" in query_str.lower():
                query_count += 1
                return mock_change_result
            # Second query is to get the plan
            elif query_count == 1 and "analysis_plan" in query_str.lower():
                query_count += 1
                return mock_plan_result
            # The remaining queries are count queries for _get_plan_change_counts
            else:
                query_count += 1
                result = Mock()
                # Return counts in order: total, applied, rejected, accepted, pending
                if query_count == 3:  # First count query (total)
                    result.scalar_one.return_value = 5
                elif query_count == 4:  # Applied count
                    result.scalar_one.return_value = 0
                elif query_count == 5:  # Rejected count
                    result.scalar_one.return_value = 0
                elif query_count == 6:  # Accepted count
                    result.scalar_one.return_value = 1
                elif query_count == 7:  # Pending count
                    result.scalar_one.return_value = 4
                else:
                    result.scalar_one.return_value = 0
                return result

        mock_db.execute = async_execute
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Update the change object to reflect the update
        mock_change.accepted = True

        response = client.patch(
            f"/api/analysis/changes/{change_id}/status", json={"accepted": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == change_id
        assert data["field"] == "title"
        assert data["proposed_value"] == "New Title"
        # Note: The actual value update happens in the mock, not in the response

    def test_update_change_status_applied_error(self, client, mock_db):
        """Test error when trying to update an already applied change."""
        change_id = 1

        # Mock applied change
        mock_change = Mock()
        mock_change.id = change_id
        mock_change.applied = True

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_change
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.patch(
            f"/api/analysis/changes/{change_id}/status", json={"accepted": True}
        )

        assert response.status_code == 400
        assert "Cannot modify an applied change" in response.json()["detail"]

    def test_cancel_plan(self, client, mock_db):
        """Test cancelling an analysis plan."""
        plan_id = 1

        # Mock plan
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.status = "draft"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        response = client.patch(f"/api/analysis/plans/{plan_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == plan_id
        assert "cancelled" in data["message"]

    def test_cancel_applied_plan_error(self, client, mock_db):
        """Test error when trying to cancel an already applied plan."""
        plan_id = 1

        # Mock applied plan
        mock_plan = Mock()
        mock_plan.id = plan_id
        mock_plan.status = PlanStatus.APPLIED

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.patch(f"/api/analysis/plans/{plan_id}/cancel")

        assert response.status_code == 400
        assert "Cannot cancel an already applied plan" in response.json()["detail"]
