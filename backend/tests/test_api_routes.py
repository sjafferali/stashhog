"""Tests for API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_db, get_stash_client
from app.main import app
from app.models import AnalysisPlan, Job, Scene, Setting
from app.models.job import JobStatus, JobType


# Mock dependencies
@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    # Mock the execute method
    db.execute = AsyncMock()
    db.scalars = Mock()
    db.scalar_one = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_stash_client():
    """Mock Stash client."""
    client = AsyncMock()
    return client


@pytest.fixture
def client(mock_db, mock_stash_client):
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_stash_client] = lambda: mock_stash_client

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


class TestHealthRoutes:
    """Test health check routes."""

    def test_health_check(self, client, mock_db):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_health_check(self, client, mock_db):
        """Test API health check."""
        response = client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_health_ping(self, client):
        """Test API health ping."""
        response = client.get("/api/health/ping")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data


class TestSceneRoutes:
    """Test scene API routes."""

    def test_list_scenes(self, client, mock_db):
        """Test listing scenes."""
        # Mock the count query result
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 2

        # Mock scenes with all required fields
        from datetime import datetime

        mock_scenes = [
            Mock(
                spec=Scene,
                id="1",
                title="Scene 1",
                path="/path/1.mp4",
                paths=["/path/1.mp4"],
                created_date=datetime.now(),
                updated_date=datetime.now(),
                date=None,
                scene_date=None,
                rating=None,
                organized=False,
                analyzed=False,
                performers=[],
                tags=[],
                studio=None,
                details=None,
                last_synced=datetime.now(),
                # Metadata fields
                duration=1800.5,
                size=1024000000,
                width=1920,
                height=1080,
                framerate=30.0,
                bitrate=5000,
                codec="h264",
                video_codec="h264",
            ),
            Mock(
                spec=Scene,
                id="2",
                title="Scene 2",
                path="/path/2.mp4",
                paths=["/path/2.mp4"],
                created_date=datetime.now(),
                updated_date=datetime.now(),
                date=None,
                scene_date=None,
                rating=None,
                organized=False,
                analyzed=False,
                performers=[],
                tags=[],
                studio=None,
                details=None,
                last_synced=datetime.now(),
                # Metadata fields
                duration=2400.0,
                size=2048000000,
                width=3840,
                height=2160,
                framerate=60.0,
                bitrate=10000,
                codec="h265",
                video_codec="h265",
            ),
        ]

        # Mock the scenes query result
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.unique.return_value.all.return_value = (
            mock_scenes
        )

        # Set up execute to return different results based on the query
        mock_db.execute.side_effect = [mock_count_result, mock_scenes_result]

        response = client.get("/api/scenes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_scene(self, client, mock_db):
        """Test getting a single scene."""
        from datetime import datetime

        mock_scene = Mock(spec=Scene)
        mock_scene.id = "123"
        mock_scene.title = "Test Scene"
        mock_scene.path = "/path/test.mp4"
        mock_scene.paths = ["/path/test.mp4"]
        mock_scene.created_date = datetime.now()
        mock_scene.updated_date = datetime.now()
        mock_scene.date = None
        mock_scene.scene_date = None
        mock_scene.rating = None
        mock_scene.organized = False
        mock_scene.analyzed = False
        mock_scene.performers = []
        mock_scene.tags = []
        mock_scene.studio = None
        mock_scene.details = None
        mock_scene.last_synced = datetime.now()
        # Metadata fields
        mock_scene.duration = 1800.5
        mock_scene.size = 1024000000
        mock_scene.width = 1920
        mock_scene.height = 1080
        mock_scene.framerate = 30.0
        mock_scene.bitrate = 5000
        mock_scene.codec = "h264"
        mock_scene.video_codec = "h264"

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_scene
        mock_db.execute.return_value = mock_result

        response = client.get("/api/scenes/123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "123"
        assert data["title"] == "Test Scene"

    def test_get_scene_not_found(self, client, mock_db):
        """Test getting non-existent scene."""
        # Mock the query result to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/scenes/nonexistent")
        assert response.status_code == 404


class TestJobRoutes:
    """Test job API routes."""

    def test_list_jobs(self, client, mock_db):
        """Test listing jobs."""
        # Mock the JobService instance
        from app.core.dependencies import get_job_service

        mock_job_service = Mock()

        # Mock active jobs from JobService
        mock_job_service.get_active_jobs = AsyncMock(return_value=[])

        # Override the dependency
        app.dependency_overrides[get_job_service] = lambda: mock_job_service

        # Mock database query for completed jobs
        from datetime import datetime

        mock_job = Mock(spec=Job)
        mock_job.id = "job1"
        mock_job.type = JobType.SYNC_ALL
        mock_job.status = JobStatus.COMPLETED
        mock_job.created_at = datetime.now()
        mock_job.updated_at = datetime.now()
        mock_job.completed_at = datetime.now()
        mock_job.progress = 100
        mock_job.job_metadata = {}
        mock_job.result = {}
        mock_job.error = None

        # Mock the jobs query
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_job]
        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value = mock_scalars

        # Set up execute to return the jobs query result
        mock_db.execute.return_value = mock_jobs_result

        try:
            response = client.get("/api/jobs")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "job1"
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_job_service, None)

    def test_get_job(self, client, mock_db):
        """Test getting a single job."""
        # Mock the JobService instance
        from app.core.dependencies import get_job_service

        mock_job_service = Mock()

        # Mock job from JobService (not found in active queue)
        mock_job_service.get_job = AsyncMock(return_value=None)
        # Mock get_job_logs to not exist
        (
            delattr(mock_job_service, "get_job_logs")
            if hasattr(mock_job_service, "get_job_logs")
            else None
        )

        # Override the dependency
        app.dependency_overrides[get_job_service] = lambda: mock_job_service

        # Mock job from database
        from datetime import datetime

        mock_job = Mock(spec=Job)
        mock_job.id = "job1"
        mock_job.type = JobType.ANALYSIS
        mock_job.status = JobStatus.RUNNING
        mock_job.progress = 50
        mock_job.created_at = datetime.now()
        mock_job.updated_at = datetime.now()
        mock_job.completed_at = None
        mock_job.job_metadata = {"scenes": 100}
        mock_job.result = None
        mock_job.error = None

        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_result

        try:
            response = client.get("/api/jobs/job1")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "job1"
            assert data["progress"] == 50
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_job_service, None)

    def test_cancel_job(self, client, mock_db):
        """Test cancelling a job."""
        from app.core.dependencies import get_job_service

        mock_job_service = Mock()
        # Mock an active job
        mock_active_job = Mock()
        mock_active_job.id = "job1"
        mock_job_service.get_job = AsyncMock(return_value=mock_active_job)
        mock_job_service.cancel_job = AsyncMock(return_value=True)

        # Override the dependency
        app.dependency_overrides[get_job_service] = lambda: mock_job_service

        try:
            response = client.post("/api/jobs/job1/cancel")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "cancelled successfully" in data["message"]

            mock_job_service.cancel_job.assert_called_once_with("job1", mock_db)
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_job_service, None)


class TestAnalysisRoutes:
    """Test analysis API routes."""

    def test_list_analysis_plans(self, client, mock_db):
        """Test listing analysis plans."""
        from datetime import datetime

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock plan
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = 1
        mock_plan.name = "Test Plan"
        mock_plan.status = "draft"
        mock_plan.total_scenes = 10
        mock_plan.analyzed_scenes = 5
        mock_plan.created_at = datetime.now()
        mock_plan.completed_at = None
        mock_plan.plan_metadata = {}

        # Mock plans query
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_plan]
        mock_plans_result = Mock()
        mock_plans_result.scalars.return_value = mock_scalars

        # Mock change count query
        mock_change_count_result = Mock()
        mock_change_count_result.scalar_one.return_value = 3

        # Mock scene count query
        mock_scene_count_result = Mock()
        mock_scene_count_result.scalar_one.return_value = 2

        # Set up execute to return different results
        mock_db.execute.side_effect = [
            mock_count_result,  # total count
            mock_plans_result,  # plans list
            mock_change_count_result,  # changes for plan
            mock_scene_count_result,  # scenes for plan
        ]

        response = client.get("/api/analysis/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Test Plan"

    def test_get_analysis_plan(self, client, mock_db):
        """Test getting a single analysis plan."""
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = 1
        mock_plan.name = "Test Plan"
        mock_plan.status = "completed"
        mock_plan.total_scenes = 10
        mock_plan.analyzed_scenes = 10
        mock_plan.created_at = datetime.now()
        mock_plan.completed_at = datetime.now()
        mock_plan.changes = []
        mock_plan.plan_metadata = {}

        # Mock execute for plan query
        mock_plan_result = Mock()
        mock_plan_result.scalar_one_or_none.return_value = mock_plan

        # Mock execute for changes query
        mock_changes_result = Mock()
        mock_changes_result.all.return_value = []

        # Set up execute to return different results
        mock_db.execute.side_effect = [
            mock_plan_result,  # plan query
            mock_changes_result,  # changes query
        ]

        response = client.get("/api/analysis/plans/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "completed"


class TestSettingsRoutes:
    """Test settings API routes."""

    def test_list_settings(self, client, mock_db):
        """Test listing settings."""
        # Mock the execute and scalars methods
        mock_result = Mock()
        mock_scalars = Mock()
        mock_settings = [
            Mock(
                spec=Setting, key="app.name", value="StashHog", description="App name"
            ),
            Mock(
                spec=Setting, key="sync.interval", value=30, description="Sync interval"
            ),
        ]
        mock_scalars.all.return_value = mock_settings
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        response = client.get("/api/settings/")
        assert response.status_code == 200
        data = response.json()
        # The endpoint returns a list of settings
        assert isinstance(data, list)
        assert len(data) > 0
        # Check that each setting has the expected structure
        for setting in data:
            assert "key" in setting
            assert "value" in setting
            assert "description" in setting

    def test_get_setting(self, client, mock_db):
        """Test getting a single setting."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "app.debug"
        mock_setting.value = False
        mock_setting.description = "Debug mode"

        # Mock execute result for single setting
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting

        mock_db.execute.return_value = mock_result

        response = client.get("/api/settings/app.debug")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "app.debug"
        assert data["value"] is False

    def test_update_setting(self, client, mock_db):
        """Test updating a setting."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "app.debug"
        mock_setting.value = False
        mock_setting.description = "Debug mode"

        # Mock execute result for finding setting
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting

        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        response = client.put("/api/settings/app.debug", json={"value": True})
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "app.debug"
        # The mock will have been updated
        assert mock_setting.value is True
        mock_db.commit.assert_called_once()


class TestSyncRoutes:
    """Test sync API routes."""

    def test_sync_all(self, client, mock_db):
        """Test syncing all entities."""
        # Mock job service
        from app.core.dependencies import get_job_service

        mock_job_service = Mock()
        mock_job = Mock()
        mock_job.id = "test-job-id"
        mock_job.type = "sync_all"
        mock_job.status = "pending"
        mock_job.progress = 0
        mock_job.created_at = datetime.now()
        mock_job.updated_at = datetime.now()
        mock_job.started_at = None
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        # Override the dependency
        app.dependency_overrides[get_job_service] = lambda: mock_job_service

        try:
            response = client.post("/api/sync/all")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-job-id"
            assert data["type"] in ["sync_all", "SYNC_ALL"]
            assert data["status"] == "pending"
            assert data["progress"] == 0

            # Verify create_job was called correctly
            mock_job_service.create_job.assert_called_once()
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_job_service, None)

    def test_sync_scenes(self, client, mock_db):
        """Test syncing scenes only."""
        # Mock job service
        from app.core.dependencies import get_job_service

        mock_job_service = Mock()
        mock_job = Mock()
        mock_job.id = "test-job-id"
        mock_job.type = "SYNC_SCENES"
        mock_job.status = "pending"
        mock_job.progress = 0
        mock_job.created_at = datetime.now()
        mock_job.updated_at = datetime.now()
        mock_job.started_at = None
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        # Override the dependency
        app.dependency_overrides[get_job_service] = lambda: mock_job_service

        try:
            response = client.post("/api/sync/scenes")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-job-id"
            assert data["type"] in ["scene_sync", "SYNC_SCENES"]
            assert data["status"] == "pending"

            # Verify create_job was called correctly
            mock_job_service.create_job.assert_called_once()
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_job_service, None)


class TestEntityRoutes:
    """Test entity (performers, tags, studios) routes."""

    def test_list_performers(self, test_client):
        """Test listing performers."""
        # Use test_client fixture instead of client
        response = test_client.get("/api/entities/performers")
        assert response.status_code == 200
        data = response.json()
        # With empty test database, should return empty list
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_tags(self, test_client):
        """Test listing tags."""
        response = test_client.get("/api/entities/tags")
        assert response.status_code == 200
        data = response.json()
        # With empty test database, should return empty list
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_studios(self, test_client):
        """Test listing studios."""
        response = test_client.get("/api/entities/studios")
        assert response.status_code == 200
        data = response.json()
        # With empty test database, should return empty list
        assert isinstance(data, list)
        assert len(data) == 0
