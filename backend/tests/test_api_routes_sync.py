"""Tests for sync API routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.job import JobStatus, JobType
from app.services.download_check_service import download_check_service
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
        assert data["type"] == "sync"
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
        """Test syncing specific scenes."""
        response = client.post(
            "/api/sync/scenes", json={"scene_ids": ["scene1", "scene2"]}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "job-456"
        assert data["type"] == "scene_sync"
        assert data["status"] == "pending"
        assert data["parameters"]["scene_ids"] == ["scene1", "scene2"]

        # Verify job service was called
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC_SCENES
        assert call_args.kwargs["metadata"] == {"scene_ids": ["scene1", "scene2"]}

    def test_sync_specific_scenes(self, client, mock_db, mock_job_service):
        """Test syncing specific scenes."""
        scene_ids = ["scene1", "scene2", "scene3"]
        response = client.post("/api/sync/scenes", json={"scene_ids": scene_ids})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["scene_ids"] == scene_ids

        # Verify job service was called with scene IDs
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["metadata"]["scene_ids"] == scene_ids

    def test_sync_scenes_with_force(self, client, mock_db, mock_job_service):
        """Test sync scenes (force is always true internally)."""
        scene_ids = ["scene1"]
        response = client.post("/api/sync/scenes", json={"scene_ids": scene_ids})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["parameters"]["scene_ids"] == scene_ids

        # Verify job service was called without force in metadata
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["metadata"] == {"scene_ids": scene_ids}


class TestSyncPerformersEndpoint:
    """Tests for the sync performers endpoint (removed)."""

    def test_sync_performers_success(self, client, mock_db, mock_job_service):
        """Test that sync performers endpoint no longer exists."""
        response = client.post("/api/sync/performers")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Endpoint should not exist

    def test_sync_performers_with_force(self, client, mock_db, mock_job_service):
        """Test that sync performers endpoint no longer exists."""
        response = client.post("/api/sync/performers?force=true")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Endpoint should not exist


class TestSyncTagsEndpoint:
    """Tests for the sync tags endpoint (removed)."""

    def test_sync_tags_success(self, client, mock_db, mock_job_service):
        """Test that sync tags endpoint no longer exists."""
        response = client.post("/api/sync/tags")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Endpoint should not exist

    def test_sync_tags_with_force(self, client, mock_db, mock_job_service):
        """Test that sync tags endpoint no longer exists."""
        response = client.post("/api/sync/tags?force=true")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Endpoint should not exist


class TestSyncStudiosEndpoint:
    """Tests for the sync studios endpoint (removed)."""

    def test_sync_studios_success(self, client, mock_db, mock_job_service):
        """Test that sync studios endpoint no longer exists."""
        response = client.post("/api/sync/studios")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Endpoint should not exist

    def test_sync_studios_with_force(self, client, mock_db, mock_job_service):
        """Test that sync studios endpoint no longer exists."""
        response = client.post("/api/sync/studios?force=true")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Endpoint should not exist


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

        assert data["message"] == "Cancelled 2 sync job(s)"
        assert mock_job_service.cancel_job.call_count == 2


class TestSyncStatsEndpoint:
    """Tests for the sync stats endpoint."""

    @pytest.fixture(autouse=True)
    def mock_download_service(self):
        """Mock download check service for all tests in this class."""
        # Mock the download check service's method
        download_check_service.get_pending_downloads_count = AsyncMock(return_value=0)
        yield
        # No cleanup needed since we're just modifying the method

    def test_get_sync_stats_no_history(self, client, mock_db, mock_stash_service):
        """Test getting sync stats with no sync history."""
        # Mock database calls
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = Mock()

            # Set up default mocks to prevent errors
            mock_scalars = Mock()
            mock_scalars.all.return_value = []
            result.scalars.return_value = mock_scalars
            result.scalar_one.return_value = 0
            result.scalar_one_or_none.return_value = None

            # Entity counts (scene, performer, tag, studio) - calls 0-3
            if call_count < 4:
                result.scalar_one.return_value = 0
            # Sync history queries - calls 4-7
            elif call_count < 8:
                result.scalar_one_or_none.return_value = None
            # Active sync jobs query - call 8 (SELECT job...)
            elif call_count == 8:
                mock_scalars.all.return_value = []
            # Analysis metrics - calls 9-12
            elif call_count < 13:
                result.scalar_one.return_value = 0
            # Active analysis jobs - call 13 (SELECT job...)
            elif call_count == 13:
                mock_scalars.all.return_value = []
            # Organization/metadata metrics - calls 14-19
            elif call_count < 20:
                result.scalar_one.return_value = 0
            # Running/completed jobs - calls 20-21 (SELECT job...)
            elif call_count < 22:
                mock_scalars.all.return_value = []
            # Failed jobs count - call 22+
            else:
                result.scalar_one.return_value = 0

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check summary section
        assert data["summary"]["scene_count"] == 0
        assert data["summary"]["performer_count"] == 0
        assert data["summary"]["tag_count"] == 0
        assert data["summary"]["studio_count"] == 0

        # Check sync section
        assert data["sync"]["last_scene_sync"] is None
        assert data["sync"]["last_performer_sync"] is None
        assert data["sync"]["last_tag_sync"] is None
        assert data["sync"]["last_studio_sync"] is None
        assert data["sync"]["pending_scenes"] == 0
        assert data["sync"]["is_syncing"] is False

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

            # Set up default mocks first to prevent errors
            mock_scalars = Mock()
            mock_scalars.all.return_value = []
            result.scalars.return_value = mock_scalars
            result.scalar_one.return_value = 0
            result.scalar_one_or_none.return_value = None

            # Entity counts (scene, performer, tag, studio) - 4 calls
            if call_count < 4:
                counts = [100, 50, 200, 30]  # scene, performer, tag, studio counts
                result.scalar_one.return_value = counts[call_count]
            # Sync history queries - 4 calls
            elif call_count < 8:
                entity_types = ["scene", "performer", "tag", "studio"]
                history = create_history_mock(entity_types[call_count - 4])
                result.scalar_one_or_none.return_value = history

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        # Mock Stash service to return pending scenes
        mock_stash_service.get_scenes.return_value = ([], 25)

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check summary section
        assert data["summary"]["scene_count"] == 100
        assert data["summary"]["performer_count"] == 50
        assert data["summary"]["tag_count"] == 200
        assert data["summary"]["studio_count"] == 30

        # Check sync section
        assert data["sync"]["last_scene_sync"] is not None
        assert data["sync"]["last_performer_sync"] is not None
        assert data["sync"]["last_tag_sync"] is not None
        assert data["sync"]["last_studio_sync"] is not None
        assert data["sync"]["pending_scenes"] == 25
        assert data["sync"]["is_syncing"] is False

    def test_get_sync_stats_with_active_sync(self, client, mock_db, mock_stash_service):
        """Test getting sync stats with active sync job."""
        # Mock responses
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            result = Mock()

            # Set up default mocks first to prevent errors
            mock_scalars = Mock()
            mock_scalars.all.return_value = []
            result.scalars.return_value = mock_scalars
            result.scalar_one.return_value = 0
            result.scalar_one_or_none.return_value = None

            # Entity counts (scene, performer, tag, studio) - 4 calls
            if call_count < 4:
                result.scalar_one.return_value = 0
            # Sync history queries - 4 calls
            elif call_count < 8:
                result.scalar_one_or_none.return_value = None
            # Active sync jobs query - 1 call
            elif call_count == 8:
                active_job = Mock()
                active_job.id = "job-123"
                active_job.type = JobType.SYNC
                active_job.status = JobStatus.RUNNING
                active_job.progress = 50
                active_job.created_at = datetime.now(timezone.utc)
                active_job.completed_at = None
                active_job.error = None
                active_job.result = {}
                active_job.job_metadata = {}
                mock_scalars = Mock()
                mock_scalars.all.return_value = [active_job]
                result.scalars.return_value = mock_scalars
            # Analysis metrics (not analyzed, not video analyzed, unorganized) - 3 calls
            elif call_count < 12:
                result.scalar_one.return_value = 0
            # Plan counts (draft, reviewing) - 2 calls
            elif call_count < 14:
                result.scalar_one.return_value = 0
            # Active analysis jobs - 1 call
            elif call_count == 14:
                mock_scalars = Mock()
                mock_scalars.all.return_value = []
                result.scalars.return_value = mock_scalars
            # Running/completed jobs queries - 2 calls
            elif call_count < 17:
                # Return mock that has all() method
                mock_scalars = Mock()
                if call_count == 15:  # First is running jobs query
                    # Return the active job created earlier
                    active_job = Mock()
                    active_job.id = "job-123"
                    active_job.type = JobType.SYNC
                    active_job.status = JobStatus.RUNNING
                    active_job.progress = 50
                    active_job.created_at = datetime.now(timezone.utc)
                    active_job.completed_at = None
                    active_job.error = None
                    active_job.result = {}
                    active_job.job_metadata = {}
                    mock_scalars.all.return_value = [active_job]
                else:
                    # Second is completed jobs query - empty
                    mock_scalars.all.return_value = []
                result.scalars.return_value = mock_scalars
            # All remaining queries - rest of calls
            else:
                # Default mock setup for scalars queries
                mock_scalars = Mock()
                mock_scalars.all.return_value = []
                result.scalars.return_value = mock_scalars
                # And for scalar queries
                result.scalar_one.return_value = 0
                result.scalar_one_or_none.return_value = None

            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["sync"]["is_syncing"] is True

    def _create_mock_result(
        self, scalar_value=0, scalars_value=None, scalar_one_or_none_value=None
    ):
        """Helper to create a mock result with common defaults."""
        result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = scalars_value or []
        result.scalars.return_value = mock_scalars
        result.scalar_one.return_value = scalar_value
        result.scalar_one_or_none.return_value = scalar_one_or_none_value
        return result

    def _handle_query_response(self, call_count, history):
        """Handle query response based on call count."""
        # Entity counts (0-3), analysis metrics (9-11), plan counts (12-13),
        # organization status (15), metadata status (16-20), failed jobs (23)
        if call_count in list(range(4)) + list(range(9, 12)) + list(range(12, 14)) + [
            15
        ] + list(range(16, 21)) + [23]:
            return self._create_mock_result(scalar_value=0)

        # First sync history call for scene
        if call_count == 4:
            return self._create_mock_result(scalar_one_or_none_value=history)

        # Other entity histories (5-7)
        if 5 <= call_count <= 7:
            return self._create_mock_result()

        # Active sync jobs (8), active analysis jobs (14), running jobs (21), completed jobs (22)
        if call_count in [8, 14, 21, 22]:
            return self._create_mock_result()

        # Default case
        return self._create_mock_result()

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
            result = self._handle_query_response(call_count, history)
            call_count += 1
            return result

        mock_db.execute.side_effect = mock_execute

        # Make Stash service raise an exception
        mock_stash_service.get_scenes.side_effect = Exception("Connection failed")

        response = client.get("/api/sync/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should use local fallback value
        assert data["sync"]["pending_scenes"] == 0  # Stash error results in 0 pending


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
