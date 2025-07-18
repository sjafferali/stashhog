"""Tests for sync API routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.job import JobStatus, JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService
from app.services.sync.models import SyncError, SyncResult, SyncStatus
from app.services.sync.sync_service import SyncService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = AsyncMock()
    db.execute = AsyncMock()
    db.close = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"sub": "test_user", "email": "test@example.com"}


@pytest.fixture
def mock_job_service():
    """Mock job service."""
    service = Mock(spec=JobService)
    mock_job = Mock()
    mock_job.id = "job-456"
    mock_job.created_at = datetime.now(timezone.utc)
    mock_job.updated_at = datetime.now(timezone.utc)
    service.create_job = AsyncMock(return_value=mock_job)
    service.cancel_job = AsyncMock()
    return service


@pytest.fixture
def mock_sync_service():
    """Mock sync service."""
    service = Mock(spec=SyncService)

    # Create a sync result for single scene sync
    started = datetime.now(timezone.utc)
    completed = datetime.now(timezone.utc)
    sync_result = SyncResult(
        job_id="job-123",
        status=SyncStatus.SUCCESS,
        total_items=1,
        processed_items=1,
        created_items=0,
        updated_items=1,
        skipped_items=0,
        failed_items=0,
        started_at=started,
        completed_at=completed,
        errors=[],
    )

    service.sync_scene_by_id = AsyncMock(return_value=sync_result)
    return service


@pytest.fixture
def mock_stash_service():
    """Mock Stash service."""
    service = Mock(spec=StashService)
    service.get_scenes = AsyncMock(return_value=([], 0))
    return service


@pytest.fixture
def client(mock_db, mock_user, mock_job_service, mock_sync_service, mock_stash_service):
    """Test client with mocked dependencies."""
    from app.core.config import Settings
    from app.core.dependencies import (
        get_current_user,
        get_db,
        get_job_service,
        get_settings,
        get_stash_service,
        get_sync_service,
    )

    # Mock settings
    settings = Settings()

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_job_service] = lambda: mock_job_service
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_sync_service] = lambda: mock_sync_service
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_service

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


class TestSyncAllEndpoint:
    """Tests for the sync all endpoint."""

    def test_sync_all_success(self, client, mock_db, mock_job_service):
        """Test successful sync all request."""
        response = client.post("/api/sync/all")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "job-456"
        assert data["type"] == "sync_all"
        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert data["parameters"]["force"] is False

        # Verify job service was called
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC
        assert call_args.kwargs["metadata"] == {"force": False}

    def test_sync_all_with_force(self, client, mock_db, mock_job_service):
        """Test sync all with force parameter."""
        response = client.post("/api/sync/all?force=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["force"] is True

        # Verify job service was called with force metadata
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["metadata"] == {"force": True}

    def test_sync_all_db_refresh(self, client, mock_db, mock_job_service):
        """Test that the job is refreshed in the database."""
        response = client.post("/api/sync/all")

        assert response.status_code == status.HTTP_200_OK

        # Verify db.refresh was called
        mock_db.refresh.assert_called_once()


class TestSyncScenesEndpoint:
    """Tests for the sync scenes endpoint."""

    def test_sync_scenes_all(self, client, mock_db, mock_job_service):
        """Test syncing all scenes."""
        response = client.post("/api/sync/scenes")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "job-456"
        assert data["type"] == "scene_sync"
        assert data["status"] == "pending"
        assert data["parameters"]["scene_ids"] is None
        assert data["parameters"]["force"] is False

        # Verify job service was called
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC_SCENES
        assert call_args.kwargs["metadata"] == {"scene_ids": None, "force": False}

    def test_sync_specific_scenes(self, client, mock_db, mock_job_service):
        """Test syncing specific scenes."""
        scene_ids = ["scene1", "scene2", "scene3"]
        response = client.post("/api/sync/scenes", json=scene_ids)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["scene_ids"] == scene_ids

        # Verify job service was called with scene IDs
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["metadata"]["scene_ids"] == scene_ids

    def test_sync_scenes_with_force(self, client, mock_db, mock_job_service):
        """Test sync scenes with force parameter."""
        scene_ids = ["scene1"]
        response = client.post("/api/sync/scenes?force=true", json=scene_ids)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["force"] is True
        assert data["parameters"]["scene_ids"] == scene_ids

        # Verify job service was called with force
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["metadata"]["force"] is True


class TestSyncPerformersEndpoint:
    """Tests for the sync performers endpoint."""

    def test_sync_performers_success(self, client, mock_db, mock_job_service):
        """Test successful sync performers request."""
        response = client.post("/api/sync/performers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "job-456"
        assert data["type"] == "sync_performers"
        assert data["status"] == "pending"
        assert data["parameters"]["force"] is False

        # Verify job service was called
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC_PERFORMERS

    def test_sync_performers_with_force(self, client, mock_db, mock_job_service):
        """Test sync performers with force parameter."""
        response = client.post("/api/sync/performers?force=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["force"] is True


class TestSyncTagsEndpoint:
    """Tests for the sync tags endpoint."""

    def test_sync_tags_success(self, client, mock_db, mock_job_service):
        """Test successful sync tags request."""
        response = client.post("/api/sync/tags")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "job-456"
        assert data["type"] == "sync_tags"
        assert data["status"] == "pending"
        assert data["parameters"]["force"] is False

        # Verify job service was called
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC_TAGS

    def test_sync_tags_with_force(self, client, mock_db, mock_job_service):
        """Test sync tags with force parameter."""
        response = client.post("/api/sync/tags?force=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["force"] is True


class TestSyncStudiosEndpoint:
    """Tests for the sync studios endpoint."""

    def test_sync_studios_success(self, client, mock_db, mock_job_service):
        """Test successful sync studios request."""
        response = client.post("/api/sync/studios")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "job-456"
        assert data["type"] == "sync_studios"
        assert data["status"] == "pending"
        assert data["parameters"]["force"] is False

        # Verify job service was called
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC_STUDIOS

    def test_sync_studios_with_force(self, client, mock_db, mock_job_service):
        """Test sync studios with force parameter."""
        response = client.post("/api/sync/studios?force=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["force"] is True


class TestSyncSingleSceneEndpoint:
    """Tests for the sync single scene endpoint."""

    def test_sync_single_scene_success(self, client, mock_sync_service):
        """Test successful single scene sync."""
        scene_id = "scene123"
        response = client.post(f"/api/sync/scene/{scene_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["job_id"] == "job-123"
        assert data["status"] == "success"
        assert data["total_items"] == 1
        assert data["processed_items"] == 1
        assert data["updated_items"] == 1
        assert data["duration_seconds"] is not None  # Calculated from timestamps
        assert data["errors"] == []

        # Verify sync service was called
        mock_sync_service.sync_scene_by_id.assert_called_once_with(scene_id)

    def test_sync_single_scene_with_errors(self, client, mock_sync_service):
        """Test single scene sync with errors."""
        scene_id = "scene123"

        # Set up sync result with errors
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)
        sync_result = SyncResult(
            job_id="job-123",
            status=SyncStatus.PARTIAL,
            total_items=1,
            processed_items=1,
            created_items=0,
            updated_items=0,
            skipped_items=0,
            failed_items=1,
            started_at=started,
            completed_at=completed,
            errors=[
                SyncError(
                    entity_type="scene",
                    entity_id=scene_id,
                    error_message="Failed to fetch scene from Stash",
                )
            ],
        )

        mock_sync_service.sync_scene_by_id.return_value = sync_result

        response = client.post(f"/api/sync/scene/{scene_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "partial"
        assert data["failed_items"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["entity"] == "scene"
        assert data["errors"][0]["id"] == scene_id
        assert data["errors"][0]["message"] == "Failed to fetch scene from Stash"

    def test_sync_single_scene_not_found(self, client, mock_sync_service):
        """Test single scene sync when scene not found."""
        scene_id = "nonexistent"

        # Create a sync result indicating failure
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)
        sync_result = SyncResult(
            job_id=None,
            status=SyncStatus.FAILED,
            total_items=0,
            processed_items=0,
            created_items=0,
            updated_items=0,
            skipped_items=0,
            failed_items=1,
            started_at=started,
            completed_at=completed,
            errors=[
                SyncError(
                    entity_type="scene",
                    entity_id=scene_id,
                    error_message=f"Scene {scene_id} not found in Stash",
                )
            ],
        )

        mock_sync_service.sync_scene_by_id.return_value = sync_result

        response = client.post(f"/api/sync/scene/{scene_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "failed"
        assert data["failed_items"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["message"] == f"Scene {scene_id} not found in Stash"


class TestSyncHistoryEndpoint:
    """Tests for the sync history endpoint."""

    def test_get_sync_history_default(self, client, mock_db):
        """Test getting sync history with default parameters."""
        # Mock sync history items
        history_items = []
        for i in range(3):
            item = Mock()
            item.id = f"history-{i}"
            item.entity_type = "scene"
            item.status = "completed"
            item.started_at = datetime.now(timezone.utc)
            item.completed_at = datetime.now(timezone.utc)
            item.items_synced = 100
            item.items_created = 10
            item.items_updated = 50
            item.items_failed = 0
            item.error_details = None
            history_items.append(item)

        # Mock the database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = history_items
        mock_db.execute.return_value = mock_result

        response = client.get("/api/sync/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 3
        for i, item in enumerate(data):
            assert item["id"] == f"history-{i}"
            assert item["entity_type"] == "scene"
            assert item["status"] == "completed"
            assert item["total_items"] == 100
            assert item["created_items"] == 10
            assert item["updated_items"] == 50
            assert item["failed_items"] == 0

    def test_get_sync_history_with_pagination(self, client, mock_db):
        """Test getting sync history with pagination."""
        # Mock empty result for offset
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = client.get("/api/sync/history?limit=5&offset=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data == []

        # Verify query was executed with correct limit/offset
        mock_db.execute.assert_called_once()

    def test_get_sync_history_with_errors(self, client, mock_db):
        """Test getting sync history with error details."""
        # Mock history item with error
        item = Mock()
        item.id = "history-error"
        item.entity_type = "performer"
        item.status = "failed"
        item.started_at = datetime.now(timezone.utc)
        item.completed_at = None
        item.items_synced = 50
        item.items_created = 10
        item.items_updated = 30
        item.items_failed = 10
        item.error_details = "Connection timeout"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [item]
        mock_db.execute.return_value = mock_result

        response = client.get("/api/sync/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 1
        assert data[0]["status"] == "failed"
        assert data[0]["failed_items"] == 10
        assert data[0]["error"] == "Connection timeout"
        assert data[0]["completed_at"] is None


class TestStopSyncEndpoint:
    """Tests for the stop sync endpoint."""

    def test_stop_sync_no_running_jobs(self, client, mock_db, mock_job_service):
        """Test stopping sync when no jobs are running."""
        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = client.post("/api/sync/stop")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["message"] == "Cancelled 0 sync job(s)"
        mock_job_service.cancel_job.assert_not_called()

    def test_stop_sync_with_running_jobs(self, client, mock_db, mock_job_service):
        """Test stopping sync with running jobs."""
        # Mock running jobs
        jobs = []
        for i in range(3):
            job = Mock()
            job.id = f"job-{i}"
            job.type = JobType.SYNC_SCENES
            job.status = JobStatus.RUNNING
            jobs.append(job)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = jobs
        mock_db.execute.return_value = mock_result

        response = client.post("/api/sync/stop")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["message"] == "Cancelled 3 sync job(s)"

        # Verify cancel was called for each job
        assert mock_job_service.cancel_job.call_count == 3
        for i in range(3):
            mock_job_service.cancel_job.assert_any_call(f"job-{i}", mock_db)

    def test_stop_sync_mixed_job_types(self, client, mock_db, mock_job_service):
        """Test stopping sync with different job types."""
        # Mock various sync job types
        job_types = [
            JobType.SYNC,
            JobType.SYNC_SCENES,
            JobType.SYNC_PERFORMERS,
            JobType.SYNC_TAGS,
            JobType.SYNC_STUDIOS,
        ]

        jobs = []
        for i, job_type in enumerate(job_types):
            job = Mock()
            job.id = f"job-{i}"
            job.type = job_type
            job.status = JobStatus.PENDING
            jobs.append(job)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = jobs
        mock_db.execute.return_value = mock_result

        response = client.post("/api/sync/stop")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["message"] == "Cancelled 5 sync job(s)"
        assert mock_job_service.cancel_job.call_count == 5


class TestSyncStatsEndpoint:
    """Tests for the sync stats endpoint."""

    def test_get_sync_stats_no_history(self, client, mock_db, mock_stash_service):
        """Test getting sync stats with no sync history."""
        # Mock database calls
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = Mock()

            # First 4 calls are for sync history (return None for each)
            if call_count < 4:
                result.scalar_one_or_none.return_value = None
            # Next 4 calls are for entity counts (return 0 for each)
            elif call_count < 8:
                result.scalar_one.return_value = 0
            # Last call is for active jobs (return empty list)
            else:
                result.scalars.return_value.all.return_value = []

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["scene_count"] == 0
        assert data["performer_count"] == 0
        assert data["tag_count"] == 0
        assert data["studio_count"] == 0
        assert data["last_scene_sync"] is None
        assert data["last_performer_sync"] is None
        assert data["last_tag_sync"] is None
        assert data["last_studio_sync"] is None
        assert data["pending_scenes"] == 0
        assert data["is_syncing"] is False

    def test_get_sync_stats_with_data(self, client, mock_db, mock_stash_service):
        """Test getting sync stats with existing data."""

        # Mock sync history for each entity type
        def create_history_mock(entity_type):
            history = Mock()
            history.entity_type = entity_type
            history.status = "completed"
            history.completed_at = datetime.now(timezone.utc)
            return history

        # Set up different responses for different entity types
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = Mock()

            # First 4 calls are for sync history
            if call_count < 4:
                entity_types = ["scene", "performer", "tag", "studio"]
                history = create_history_mock(entity_types[call_count])
                result.scalar_one_or_none.return_value = history
            # Next 4 calls are for entity counts
            elif call_count < 8:
                counts = [100, 50, 200, 30]  # scene, performer, tag, studio counts
                result.scalar_one.return_value = counts[call_count - 4]
            # Last call is for active jobs
            else:
                result.scalars.return_value.all.return_value = []

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        # Mock Stash service to return pending scenes
        mock_stash_service.get_scenes.return_value = ([], 25)

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["scene_count"] == 100
        assert data["performer_count"] == 50
        assert data["tag_count"] == 200
        assert data["studio_count"] == 30
        assert data["last_scene_sync"] is not None
        assert data["last_performer_sync"] is not None
        assert data["last_tag_sync"] is not None
        assert data["last_studio_sync"] is not None
        assert data["pending_scenes"] == 25
        assert data["is_syncing"] is False

    def test_get_sync_stats_with_active_sync(self, client, mock_db, mock_stash_service):
        """Test getting sync stats with active sync job."""
        # Mock responses
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = Mock()

            # First 4 calls return no sync history
            if call_count < 4:
                result.scalar_one_or_none.return_value = None
            # Next 4 calls return zero counts
            elif call_count < 8:
                result.scalar_one.return_value = 0
            # Last call returns active sync jobs
            else:
                active_job = Mock()
                active_job.type = JobType.SYNC
                active_job.status = JobStatus.RUNNING
                result.scalars.return_value.all.return_value = [active_job]

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["is_syncing"] is True

    def test_get_sync_stats_stash_error_fallback(
        self, client, mock_db, mock_stash_service
    ):
        """Test sync stats when Stash API fails, falling back to local check."""
        # Mock sync history with last sync time
        history = Mock()
        history.entity_type = "scene"
        history.status = "completed"
        history.completed_at = datetime.now(timezone.utc)

        # Set up mock responses
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = Mock()

            if call_count == 0:  # First call for scene history
                result.scalar_one_or_none.return_value = history
            elif call_count < 4:  # Other entity histories
                result.scalar_one_or_none.return_value = None
            elif call_count < 8:  # Entity counts
                result.scalar_one.return_value = 0
            elif call_count == 8:  # Pending scenes fallback query
                result.scalar_one.return_value = 5
            else:  # Active jobs
                result.scalars.return_value.all.return_value = []

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        # Make Stash service raise an exception
        mock_stash_service.get_scenes.side_effect = Exception("Connection failed")

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should use local fallback value
        assert data["pending_scenes"] == 5


class TestJobTypeMapping:
    """Tests for the job type mapping function."""

    def test_job_type_mapping(self):
        """Test the _map_job_type function."""
        from app.api.routes.sync import _map_job_type

        assert _map_job_type("sync") == "sync_all"
        assert _map_job_type("sync_scenes") == "scene_sync"
        assert _map_job_type("sync_performers") == "sync_all"
        assert _map_job_type("sync_tags") == "sync_all"
        assert _map_job_type("sync_studios") == "sync_all"
        assert _map_job_type("sync_all") == "sync_all"
        assert _map_job_type("unknown") == "sync_all"  # Default case
