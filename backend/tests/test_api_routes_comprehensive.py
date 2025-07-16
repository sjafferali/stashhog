"""Comprehensive tests for API routes to improve coverage."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_db
from app.models import AnalysisPlan, Job, Scene, Setting
from app.models.job import JobStatus, JobType
from tests.test_app import create_test_app


# Mock database session
@pytest.fixture
def mock_db():
    """Create mock database session."""
    # Create a mock that can be used as both Session and AsyncSession
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.query = Mock()  # For sync session compatibility
    db.close = AsyncMock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def mock_stash_client():
    """Create mock Stash client."""
    client = AsyncMock()
    client.test_connection = AsyncMock(return_value=True)
    client.find_scenes = AsyncMock(return_value={"count": 0, "scenes": []})
    client.find_scene = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = AsyncMock()
    client.test_connection = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_job_service():
    """Create mock Job service."""
    service = AsyncMock()
    service.enqueue = AsyncMock(return_value="test-job-id")
    service.get_job = AsyncMock(return_value=None)
    service.cancel_job = AsyncMock(return_value=True)
    service.get_active_jobs = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_sync_service():
    """Create mock Sync service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_analysis_service():
    """Create mock Analysis service."""
    service = AsyncMock()
    service.create_analysis_plan = AsyncMock()
    return service


@pytest.fixture
def client(
    mock_db,
    mock_stash_client,
    mock_openai_client,
    mock_job_service,
    mock_sync_service,
    mock_analysis_service,
):
    """Create test client with mocked dependencies."""
    from app.core.dependencies import (
        get_analysis_service,
        get_job_service,
        get_openai_client,
        get_stash_client,
        get_stash_service,
        get_sync_service,
    )

    # Create test app without lifespan
    app = create_test_app()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_stash_client] = lambda: mock_stash_client
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_client
    app.dependency_overrides[get_openai_client] = lambda: mock_openai_client
    app.dependency_overrides[get_job_service] = lambda: mock_job_service
    app.dependency_overrides[get_sync_service] = lambda: mock_sync_service
    app.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestHealthRoutes:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_check(self, client, mock_db):
        """Test readiness check."""
        # Mock database check - create async context manager
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(1,))

        # Make execute return an awaitable that returns the mock result
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"]["status"] == "ready"


class TestSceneRoutes:
    """Test scene management endpoints."""

    def test_list_scenes(self, client, mock_db):
        """Test listing scenes."""
        # Mock database query for count
        count_result = Mock()
        count_result.scalar_one = Mock(return_value=2)

        # Mock scenes with all required relationships
        mock_studio = Mock()
        mock_studio.id = "studio1"
        mock_studio.name = "Test Studio"
        mock_studio.scene_count = 5
        mock_performer = Mock()
        mock_performer.id = "perf1"
        mock_performer.name = "Test Performer"
        mock_performer.scene_count = 3
        mock_tag = Mock()
        mock_tag.id = "tag1"
        mock_tag.name = "Test Tag"
        mock_tag.scene_count = 2

        scenes = [
            Mock(
                spec=Scene,
                id="1",
                title="Scene 1",
                paths=["path1"],
                organized=True,
                details="Details 1",
                created_date=datetime.utcnow(),
                scene_date=datetime.utcnow(),
                studio=mock_studio,
                performers=[mock_performer],
                tags=[mock_tag],
                last_synced=datetime.utcnow(),
            ),
            Mock(
                spec=Scene,
                id="2",
                title="Scene 2",
                paths=["path2"],
                organized=False,
                details="Details 2",
                created_date=datetime.utcnow(),
                scene_date=datetime.utcnow(),
                studio=None,
                performers=[],
                tags=[],
                last_synced=datetime.utcnow(),
            ),
        ]

        # Mock scenes result
        scenes_result = Mock()
        scenes_result.scalars = Mock(
            return_value=Mock(
                unique=Mock(return_value=Mock(all=Mock(return_value=scenes)))
            )
        )

        # Set up execute side effects
        mock_db.execute = AsyncMock(side_effect=[count_result, scenes_result])

        response = client.get("/api/scenes/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_scene(self, client, mock_db):
        """Test getting a single scene."""
        # Mock scene with all required attributes
        mock_studio = Mock()
        mock_studio.id = "studio1"
        mock_studio.name = "Test Studio"
        mock_studio.scene_count = 5
        mock_performer = Mock()
        mock_performer.id = "perf1"
        mock_performer.name = "Test Performer"
        mock_performer.scene_count = 3
        mock_tag = Mock()
        mock_tag.id = "tag1"
        mock_tag.name = "Test Tag"
        mock_tag.scene_count = 2

        scene = Mock(
            spec=Scene,
            id="1",
            title="Test Scene",
            paths=["path1"],
            organized=True,
            details="Test details",
            created_date=datetime.utcnow(),
            scene_date=datetime.utcnow(),
            studio=mock_studio,
            performers=[mock_performer],
            tags=[mock_tag],
            last_synced=datetime.utcnow(),
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=scene)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/scenes/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "1"
        assert data["title"] == "Test Scene"

    def test_get_scene_not_found(self, client, mock_db):
        """Test getting non-existent scene."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/scenes/999")
        assert response.status_code == 404

    def test_update_scene(self, client):
        """Test updating a scene - endpoint doesn't exist."""
        update_data = {"title": "New Title", "rating": 90}
        response = client.put("/api/scenes/1", json=update_data)

        assert response.status_code == 405  # Method not allowed

    def test_delete_scene(self, client):
        """Test deleting a scene - endpoint doesn't exist."""
        response = client.delete("/api/scenes/1")
        assert response.status_code == 405  # Method not allowed

    def test_sync_scene(self, client):
        """Test syncing a single scene - endpoint doesn't exist."""
        response = client.post("/api/scenes/1/sync")
        assert response.status_code == 404


class TestJobRoutes:
    """Test job management endpoints."""

    def test_list_jobs(self, client, mock_db):
        """Test listing jobs."""
        jobs = [
            Mock(
                spec=Job,
                id="j1",
                type=JobType.SYNC,
                status=JobStatus.COMPLETED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                progress=100,
                metadata={},
                result=None,
                error=None,
            ),
            Mock(
                spec=Job,
                id="j2",
                type=JobType.ANALYSIS,
                status=JobStatus.RUNNING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=None,
                progress=50,
                metadata={},
                result=None,
                error=None,
            ),
        ]

        with patch("app.api.routes.jobs.get_job_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_active_jobs = AsyncMock(return_value=[])

            mock_result = AsyncMock()
            mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=jobs)))
            mock_db.execute = AsyncMock(return_value=mock_result)

            response = client.get("/api/jobs")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_get_job(self, client, mock_db):
        """Test getting a single job."""
        job = Mock(
            spec=Job,
            id="j1",
            type=JobType.SYNC,
            status=JobStatus.COMPLETED,
            progress=100,
            metadata={},
            result=None,
            error=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=job)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.routes.jobs.get_job_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_job = AsyncMock(return_value=job)
            mock_service.get_job_logs = AsyncMock(return_value=None)

            response = client.get("/api/jobs/j1")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "j1"
            assert data["status"] == JobStatus.COMPLETED.value

    def test_cancel_job(self, client, mock_db, mock_job_service):
        """Test canceling a job."""
        # Use the fixture's mock_job_service which is already injected
        job_mock = Mock(id="j1", status=JobStatus.RUNNING)
        mock_job_service.get_job = AsyncMock(return_value=job_mock)
        mock_job_service.cancel_job = AsyncMock(return_value=True)

        response = client.post("/api/jobs/j1/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_retry_job(self, client, mock_db, mock_job_service):
        """Test retrying a failed job."""
        # Mock the original job from database
        mock_job = Mock(
            spec=Job,
            id="j1",
            type=JobType.SYNC,
            status=JobStatus.FAILED,
            job_metadata={"param1": "value1"},
            progress=0,
            result=None,
            error="Previous error",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_job)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock the job service to create a new job
        new_job = Mock(spec=Job, id="new-job-id")
        mock_job_service.create_job = AsyncMock(return_value=new_job)

        response = client.post("/api/jobs/j1/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_job_id"] == "new-job-id"


class TestAnalysisRoutes:
    """Test analysis endpoints."""

    def test_create_analysis(self, client, mock_job_service, mock_analysis_service):
        """Test creating analysis job."""
        # Mock the job that create_job returns
        mock_job = Mock()
        mock_job.id = "job123"
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        request_data = {
            "scene_ids": ["1", "2", "3", "4", "5"],
            "options": {"detect_performers": True, "detect_tags": True},
            "plan_name": "Test Analysis",
        }

        response = client.post("/api/analysis/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job123"
        assert data["status"] == "queued"

    def test_list_analysis_plans(self, client, mock_db):
        """Test listing analysis plans."""
        plan1 = Mock(spec=AnalysisPlan)
        plan1.id = 1
        plan1.name = "Plan 1"
        plan1.status = "pending"
        plan1.created_at = datetime.utcnow()
        plan1.plan_metadata = {}
        plan1.total_scenes = 5
        plan1.total_changes = 10

        plan2 = Mock(spec=AnalysisPlan)
        plan2.id = 2
        plan2.name = "Plan 2"
        plan2.status = "applied"
        plan2.created_at = datetime.utcnow()
        plan2.plan_metadata = {}
        plan2.total_scenes = 3
        plan2.total_changes = 5

        plans = [plan1, plan2]

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one = Mock(return_value=2)

        # Mock plan query
        mock_plan_result = Mock()
        mock_plan_result.scalars = Mock(return_value=Mock(all=Mock(return_value=plans)))

        # For each plan, we need count queries for changes and scenes
        mock_change_count_result = Mock()
        mock_change_count_result.scalar_one = Mock(return_value=10)

        mock_scene_count_result = Mock()
        mock_scene_count_result.scalar_one = Mock(return_value=5)

        # Create a list that will reset for each test
        # We need to create new instances for each call to avoid reuse issues
        side_effects = [
            mock_count_result,  # Total count
            mock_plan_result,  # Plans list
            Mock(scalar_one=Mock(return_value=10)),  # Changes count for plan 1
            Mock(scalar_one=Mock(return_value=5)),  # Scenes count for plan 1
            Mock(scalar_one=Mock(return_value=5)),  # Changes count for plan 2
            Mock(scalar_one=Mock(return_value=3)),  # Scenes count for plan 2
        ]
        mock_db.execute = AsyncMock(side_effect=side_effects)

        response = client.get("/api/analysis/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_get_analysis_plan(self, client, mock_db):
        """Test getting analysis plan details."""
        plan = Mock(spec=AnalysisPlan)
        plan.id = 1
        plan.name = "Test Plan"
        plan.status = "pending"
        plan.created_at = datetime.utcnow()
        plan.plan_metadata = {}
        plan.total_scenes = 1
        plan.total_changes = 1

        # Mock plan query
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none = Mock(return_value=plan)

        # Mock changes query
        scene = Mock()
        scene.id = "scene1"
        scene.title = "Test Scene"

        change = Mock()
        change.id = 1
        change.scene_id = "scene1"
        change.field = "tags"
        change.action = "add"
        change.current_value = []  # Should be actual list, not string
        change.proposed_value = ["tag1"]  # Should be actual list, not string
        change.confidence = 0.9
        mock_changes_result = Mock()
        mock_changes_result.all = Mock(return_value=[(change, scene)])

        mock_db.execute = AsyncMock(side_effect=[mock_plan_result, mock_changes_result])

        response = client.get("/api/analysis/plans/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert len(data["scenes"]) == 1

    def test_apply_analysis_plan(self, client, mock_db, mock_job_service):
        """Test applying an analysis plan."""
        # Mock plan query
        plan = Mock(id=1, status="draft")
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none = Mock(return_value=plan)
        mock_db.execute = AsyncMock(return_value=mock_plan_result)

        # Mock the job that create_job returns
        mock_job = Mock()
        mock_job.id = "test-job-id"
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        response = client.post("/api/analysis/plans/1/apply")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        assert data["status"] == "queued"


class TestSyncRoutes:
    """Test sync endpoints."""

    def test_sync_all(self, client, mock_job_service):
        """Test full sync."""
        mock_job = Mock()
        mock_job.id = "sync_job_123"
        mock_job.type = JobType.SYNC_ALL
        mock_job.status = JobStatus.PENDING
        mock_job.progress = 0
        mock_job.created_at = datetime.utcnow()
        mock_job.updated_at = datetime.utcnow()
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.result = None
        mock_job.error = None
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        response = client.post("/api/sync/all")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "sync_job_123"
        assert data["type"] in ["sync_all", "SYNC_ALL"]

    def test_sync_scenes(self, client, mock_job_service):
        """Test scene sync."""
        mock_job = Mock()
        mock_job.id = "sync_scenes_job_123"
        mock_job.type = JobType.SYNC_SCENES
        mock_job.status = JobStatus.PENDING
        mock_job.progress = 0
        mock_job.created_at = datetime.utcnow()
        mock_job.updated_at = datetime.utcnow()
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.result = None
        mock_job.error = None
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        response = client.post("/api/sync/scenes")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "sync_scenes_job_123"
        assert data["type"] in ["scene_sync", "SYNC_SCENES"]

    def test_sync_status(self, client):
        """Test getting sync status - endpoint doesn't exist."""
        response = client.get("/api/sync/status")
        assert response.status_code == 404


class TestSettingsRoutes:
    """Test settings endpoints."""

    def test_get_settings(self, client, mock_db):
        """Test getting settings."""
        # Mock the database query for settings
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []  # No additional settings in DB
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 8  # At least 8 settings returned
        assert any(s["key"] == "app.name" for s in data)

    def test_update_setting(self, client, mock_db):
        """Test updating a setting."""
        # Mock the setting query
        mock_setting = Mock(
            spec=Setting,
            key="sync.enabled",
            value="true",
            category="sync",
            description="Enable sync",
        )
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_setting)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.put("/api/settings/sync.enabled", json={"value": "true"})
        assert response.status_code == 200  # This endpoint actually exists

    def test_create_setting(self, client):
        """Test creating a new setting - endpoint doesn't exist."""
        setting_data = {
            "key": "new.setting",
            "value": "test",
            "description": "A new setting",
        }

        response = client.post("/api/settings", json=setting_data)
        assert response.status_code == 405  # Method not allowed


class TestEntityRoutes:
    """Test entity management endpoints."""

    def test_list_performers(self, client, mock_db):
        """Test listing performers."""
        # Mock performers query
        performer1 = Mock()
        performer1.id = "p1"
        performer1.name = "Performer 1"
        performer1.scene_count = 5

        performer2 = Mock()
        performer2.id = "p2"
        performer2.name = "Performer 2"
        performer2.scene_count = 3

        performers = [performer1, performer2]

        # Mock performer result
        mock_performer_result = Mock()
        mock_performer_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=performers))
        )

        # Mock count queries for each performer
        mock_count_result = Mock()
        mock_count_result.scalar_one = Mock(return_value=5)

        # Set up execute to return performer list first, then counts for each
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_performer_result,  # Performers list
                mock_count_result,  # Count for performer 1
                mock_count_result,  # Count for performer 2
            ]
        )

        response = client.get("/api/entities/performers")
        assert response.status_code == 200

    def test_list_tags(self, client, mock_db):
        """Test listing tags."""
        # Mock tags query
        tag1 = Mock()
        tag1.id = "t1"
        tag1.name = "Tag 1"
        tag1.scene_count = 4

        tag2 = Mock()
        tag2.id = "t2"
        tag2.name = "Tag 2"
        tag2.scene_count = 2

        tags = [tag1, tag2]

        # Mock tag result
        mock_tag_result = Mock()
        mock_tag_result.scalars = Mock(return_value=Mock(all=Mock(return_value=tags)))

        # Mock count queries for each tag
        mock_count_result = Mock()
        mock_count_result.scalar_one = Mock(return_value=3)

        # Set up execute to return tag list first, then counts for each
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_tag_result,  # Tags list
                mock_count_result,  # Count for tag 1
                mock_count_result,  # Count for tag 2
            ]
        )

        response = client.get("/api/entities/tags")
        assert response.status_code == 200

    def test_list_studios(self, client, mock_db):
        """Test listing studios."""
        # Mock studios query
        studio1 = Mock()
        studio1.id = "s1"
        studio1.name = "Studio 1"
        studio1.scene_count = 10

        studio2 = Mock()
        studio2.id = "s2"
        studio2.name = "Studio 2"
        studio2.scene_count = 7

        studios = [studio1, studio2]

        # Mock studio result
        mock_studio_result = Mock()
        mock_studio_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=studios))
        )

        # Mock count queries for each studio
        mock_count_result = Mock()
        mock_count_result.scalar_one = Mock(return_value=10)

        # Set up execute to return studio list first, then counts for each
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_studio_result,  # Studios list
                mock_count_result,  # Count for studio 1
                mock_count_result,  # Count for studio 2
            ]
        )

        response = client.get("/api/entities/studios")
        assert response.status_code == 200


class TestSchedulerRoutes:
    """Test scheduler endpoints."""

    def test_list_scheduled_tasks(self, client):
        """Test listing scheduled tasks - endpoint doesn't exist."""
        response = client.get("/api/scheduler/tasks")
        assert response.status_code == 404

    def test_create_scheduled_task(self, client):
        """Test creating a scheduled task - endpoint doesn't exist."""
        task_data = {
            "name": "Hourly Analysis",
            "task_type": "analysis",
            "cron_expression": "0 * * * *",
            "config": {"scene_ids": [1, 2, 3]},
            "enabled": True,
        }

        response = client.post("/api/scheduler/tasks", json=task_data)
        assert response.status_code == 404

    def test_toggle_scheduled_task(self, client):
        """Test toggling a scheduled task - endpoint doesn't exist."""
        response = client.post("/api/scheduler/tasks/1/toggle")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling across routes."""

    def test_validation_error(self, client):
        """Test validation error response."""
        # Invalid data for scene creation - endpoint doesn't exist
        response = client.post("/api/scenes", json={"invalid": "data"})
        assert response.status_code == 405  # Method not allowed

    def test_internal_server_error(self, client, mock_db):
        """Test internal server error handling."""
        # Make database raise an exception
        mock_db.execute = AsyncMock(side_effect=Exception("Database error"))

        # The test client may not propagate exceptions properly, so we check for error
        # The actual implementation might return 500 or raise an exception
        try:
            response = client.get("/api/scenes/")
            # If we get a response, it should be a 500 error
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
        except Exception as e:
            # If the exception propagates, that's also correct behavior
            assert "Database error" in str(e)
