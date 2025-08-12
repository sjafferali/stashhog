"""Tests for scene API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.scene import Scene


# Mock job repository at module level to avoid import issues
@pytest.fixture(autouse=True)
def mock_job_repository():
    """Mock job repository methods."""
    with (
        patch(
            "app.api.routes.scenes.job_repository.get_active_jobs_for_scenes",
            new_callable=AsyncMock,
        ) as mock_active,
        patch(
            "app.api.routes.scenes.job_repository.get_recent_jobs_for_scenes",
            new_callable=AsyncMock,
        ) as mock_recent,
    ):
        mock_active.return_value = {}
        mock_recent.return_value = {}
        yield


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"sub": "test_user", "email": "test@example.com"}


@pytest.fixture
def mock_job_service():
    """Mock job service."""
    service = AsyncMock()
    service.enqueue = AsyncMock(return_value="test-job-id")
    return service


@pytest.fixture
def mock_sync_service():
    """Mock sync service."""
    service = AsyncMock()
    return service


@pytest.fixture
def client(mock_db, mock_user, mock_job_service, mock_sync_service):
    """Test client with mocked dependencies."""
    from app.core.dependencies import (
        get_analysis_service,
        get_job_service,
        get_openai_client,
        get_stash_client,
        get_stash_service,
        get_sync_service,
    )

    # Create additional mock services that might be needed
    mock_stash_client = AsyncMock()
    mock_openai_client = AsyncMock()
    mock_analysis_service = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_job_service] = lambda: mock_job_service
    app.dependency_overrides[get_sync_service] = lambda: mock_sync_service
    app.dependency_overrides[get_stash_client] = lambda: mock_stash_client
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_client
    app.dependency_overrides[get_openai_client] = lambda: mock_openai_client
    app.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service

    # Skip lifespan events in tests to avoid initialization issues
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_scene():
    """Create a mock scene object."""
    scene = Mock(spec=Scene)
    scene.id = "stash123"
    scene.title = "Test Scene"
    scene.details = "Scene details"
    scene.rating = 5
    scene.organized = True
    scene.analyzed = False
    scene.video_analyzed = False
    scene.stash_created_at = datetime.utcnow()
    scene.stash_updated_at = datetime.utcnow()
    scene.stash_date = datetime.utcnow()
    scene.created_at = datetime.utcnow()
    scene.updated_at = datetime.utcnow()
    scene.last_synced = datetime.utcnow()
    scene.performers = []
    scene.tags = []
    scene.studio = None
    scene.markers = []

    # Create mock file
    mock_file = Mock()
    mock_file.id = "file123"
    mock_file.path = "/path/to/scene.mp4"
    mock_file.basename = "scene.mp4"
    mock_file.is_primary = True
    mock_file.duration = 3600
    mock_file.size = 1024000000
    mock_file.width = 1920
    mock_file.height = 1080
    mock_file.frame_rate = 30.0
    mock_file.bit_rate = 5000
    mock_file.video_codec = "h264"
    mock_file.audio_codec = "aac"
    mock_file.format = "mp4"
    mock_file.oshash = None
    mock_file.phash = None
    mock_file.mod_time = None

    scene.files = [mock_file]

    # Add get_primary_file method
    scene.get_primary_file = Mock(return_value=mock_file)

    scene.to_dict = Mock(
        return_value={
            "id": scene.id,
            "title": scene.title,
            "details": scene.details,
            "rating": scene.rating,
            "organized": scene.organized,
            "analyzed": scene.analyzed,
            "video_analyzed": scene.video_analyzed,
            "stash_created_at": scene.stash_created_at,
            "stash_updated_at": scene.stash_updated_at,
            "stash_date": scene.stash_date,
            "last_synced": scene.last_synced,
            "performers": [],
            "tags": [],
            "studio": None,
            "markers": [],
            "files": [
                {
                    "id": mock_file.id,
                    "path": mock_file.path,
                    "basename": mock_file.basename,
                    "is_primary": mock_file.is_primary,
                    "duration": mock_file.duration,
                    "size": mock_file.size,
                    "width": mock_file.width,
                    "height": mock_file.height,
                    "frame_rate": mock_file.frame_rate,
                    "bit_rate": mock_file.bit_rate,
                    "video_codec": mock_file.video_codec,
                    "audio_codec": mock_file.audio_codec,
                    "format": mock_file.format,
                    "oshash": mock_file.oshash,
                    "phash": mock_file.phash,
                    "mod_time": mock_file.mod_time,
                }
            ],
        }
    )
    return scene


class TestSceneRoutes:
    """Test scene API routes."""

    def test_list_scenes_no_params(self, client, mock_db, mock_scene):
        """Test listing scenes without parameters."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(mock_scene.id)

    def test_list_scenes_with_search(self, client, mock_db, mock_scene):
        """Test listing scenes with search parameter."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?search=test")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_with_pagination(self, client, mock_db):
        """Test listing scenes with pagination."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 100

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?page=2&per_page=20")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 20
        assert data["total"] == 100

    def test_get_scene_found(self, client, mock_db):
        """Test getting a scene that exists."""

        # Create complete mock scene with all required attributes
        # Create proper objects that can be serialized
        class MockStudio:
            def __init__(self):
                self.id = "studio1"
                self.name = "Test Studio"
                self.scene_count = 5

        mock_studio = MockStudio()

        class MockPerformer:
            def __init__(self):
                self.id = "perf1"
                self.name = "Test Performer"
                self.scene_count = 3
                self.gender = "male"
                self.favorite = False
                self.rating100 = None

        mock_performer = MockPerformer()

        class MockTag:
            def __init__(self):
                self.id = "tag1"
                self.name = "Test Tag"
                self.scene_count = 2

        mock_tag = MockTag()

        # Create mock file
        class MockFile:
            def __init__(self):
                self.id = "file123"
                self.path = "/path/to/scene.mp4"
                self.basename = "scene.mp4"
                self.is_primary = True
                self.duration = 1800.5
                self.size = 1024000000
                self.width = 1920
                self.height = 1080
                self.frame_rate = 30.0
                self.bit_rate = 5000
                self.video_codec = "h264"
                self.audio_codec = "aac"
                self.format = "mp4"
                self.oshash = None
                self.phash = None
                self.mod_time = None

        mock_file = MockFile()

        mock_scene = Mock(spec=Scene)
        mock_scene.id = "123"
        mock_scene.title = "Test Scene"
        mock_scene.organized = True
        mock_scene.analyzed = False
        mock_scene.video_analyzed = False
        mock_scene.details = "Scene details"
        mock_scene.stash_created_at = datetime.utcnow()
        mock_scene.stash_updated_at = datetime.utcnow()
        mock_scene.stash_date = datetime.utcnow()
        mock_scene.last_synced = datetime.utcnow()
        mock_scene.created_at = datetime.utcnow()
        mock_scene.updated_at = datetime.utcnow()
        mock_scene.studio = mock_studio
        mock_scene.performers = [mock_performer]
        mock_scene.tags = [mock_tag]
        mock_scene.markers = []
        mock_scene.files = [mock_file]

        # Add get_primary_file method
        mock_scene.get_primary_file = Mock(return_value=mock_file)

        # Mock scene query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_scene

        # Mock the unique() method for selectinload queries
        mock_unique = Mock()
        mock_unique.all.return_value = []
        mock_result.scalars.return_value.unique.return_value = mock_unique

        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get(f"/api/scenes/{mock_scene.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(mock_scene.id)
        assert data["title"] == mock_scene.title

    def test_get_scene_not_found(self, client, mock_db):
        """Test getting a scene that doesn't exist."""
        # Mock scene query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None

        # Mock the unique() method for selectinload queries
        mock_unique = Mock()
        mock_unique.all.return_value = []
        mock_result.scalars.return_value.unique.return_value = mock_unique

        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/scenes/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_update_scene(self, client, mock_db, mock_sync_service):
        """Test updating a scene."""
        # Create complete mock scene with all required attributes
        mock_studio = Mock()
        mock_studio.id = "studio1"
        mock_studio.name = "Test Studio"

        # Create mock file for update test
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.path = "/path/to/scene.mp4"
        mock_file.basename = "scene.mp4"
        mock_file.is_primary = True
        mock_file.duration = 3600
        mock_file.size = 1024000000
        mock_file.width = 1920
        mock_file.height = 1080
        mock_file.frame_rate = 30.0
        mock_file.bit_rate = 5000
        mock_file.video_codec = "h264"
        mock_file.audio_codec = "aac"
        mock_file.format = "mp4"
        mock_file.oshash = None
        mock_file.phash = None
        mock_file.mod_time = None

        mock_scene = Mock(spec=Scene)
        mock_scene.id = "1"
        mock_scene.title = "Test Scene"
        mock_scene.organized = True
        mock_scene.analyzed = False
        mock_scene.video_analyzed = False
        mock_scene.details = "Scene details"
        mock_scene.stash_created_at = datetime.utcnow()
        mock_scene.stash_updated_at = datetime.utcnow()
        mock_scene.stash_date = datetime.utcnow()
        mock_scene.last_synced = datetime.utcnow()
        mock_scene.created_at = datetime.utcnow()
        mock_scene.updated_at = datetime.utcnow()
        mock_scene.studio = mock_studio
        mock_scene.files = [mock_file]

        # Add get_primary_file method
        mock_scene.get_primary_file = Mock(return_value=mock_file)
        mock_scene.performers = []
        mock_scene.tags = []
        mock_scene.markers = []

        # Mock initial scene query for verification
        mock_result1 = Mock()
        mock_result1.scalar_one_or_none.return_value = mock_scene

        # Mock get_scene query with relationships (called after update)
        mock_result2 = Mock()
        mock_result2.scalar_one_or_none.return_value = mock_scene

        # Mock the unique() method for selectinload queries
        mock_unique = Mock()
        mock_unique.all.return_value = []
        mock_result2.scalars.return_value.unique.return_value = mock_unique

        # The update endpoint calls execute twice: once for verification, once for get_scene
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        # Mock sync service with stash_service
        mock_stash_service = AsyncMock()
        mock_stash_service.update_scene = AsyncMock(
            return_value={"id": "1", "title": "Updated Title"}
        )
        mock_sync_service.stash_service = mock_stash_service
        mock_sync_service.sync_scene_by_id = AsyncMock()

        # Mock refresh
        mock_db.refresh = AsyncMock()

        update_data = {
            "title": "Updated Title",
            "details": "Updated details",
            "rating": 4,
        }

        response = client.patch("/api/scenes/1", json=update_data)

        assert response.status_code == 200  # Scene successfully updated
        mock_stash_service.update_scene.assert_called_once_with("1", update_data)
        mock_sync_service.sync_scene_by_id.assert_called_once_with("1")

    def test_update_scene_not_found(self, client, mock_db):
        """Test updating a scene that doesn't exist."""
        # Mock scene query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.patch("/api/scenes/nonexistent-id", json={"title": "Updated"})

        assert response.status_code == 404  # Not found

    def test_delete_scene(self, client):
        """Test deleting a scene - endpoint doesn't exist."""
        response = client.delete("/api/scenes/1")

        assert response.status_code == 405  # Method not allowed

    def test_delete_scene_not_found(self, client):
        """Test deleting a scene that doesn't exist - endpoint doesn't exist."""
        response = client.delete("/api/scenes/nonexistent-id")

        assert response.status_code == 405  # Method not allowed

    def test_sync_scenes(self, client, mock_db, mock_job_service):
        """Test scene sync endpoint."""
        mock_job = Mock()
        mock_job.id = "job123"
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        response = client.post("/api/scenes/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job123"
        mock_job_service.create_job.assert_called_once()

    def test_get_scene_stats(self, client, mock_db):
        """Test getting scene statistics."""
        # Mock total scenes count
        mock_total_result = Mock()
        mock_total_result.scalar_one.return_value = 100

        # Mock organized scenes count
        mock_organized_result = Mock()
        mock_organized_result.scalar_one.return_value = 80

        # Mock tags count
        mock_tags_result = Mock()
        mock_tags_result.scalar_one.return_value = 50

        # Mock performers count
        mock_performers_result = Mock()
        mock_performers_result.scalar_one.return_value = 30

        # Mock studios count
        mock_studios_result = Mock()
        mock_studios_result.scalar_one.return_value = 20

        # Mock studio stats
        mock_studio_stats_result = Mock()
        mock_studio_stats_result.__iter__ = Mock(
            return_value=iter([("Studio 1", 25), ("Studio 2", 15)])
        )

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_total_result,
                mock_organized_result,
                mock_tags_result,
                mock_performers_result,
                mock_studios_result,
                mock_studio_stats_result,
            ]
        )

        response = client.get("/api/scenes/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_scenes"] == 100
        assert data["organized_scenes"] == 80

    def test_list_scenes_filter_by_performer(self, client, mock_db, mock_scene):
        """Test filtering scenes by performer."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?performer_ids=perf123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_filter_by_tag(self, client, mock_db, mock_scene):
        """Test filtering scenes by tag."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?tag_ids=tag123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        # Tag filter was included in the query

    def test_list_scenes_sort_by_created(self, client, mock_db):
        """Test sorting scenes by creation date."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?sort=created_at")

        assert response.status_code == 200

    def test_list_scenes_filter_by_studio(self, client, mock_db, mock_scene):
        """Test filtering scenes by studio ID."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?studio_id=studio123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_filter_by_organized(self, client, mock_db, mock_scene):
        """Test filtering scenes by organized status."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?organized=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_filter_by_analyzed(self, client, mock_db):
        """Test filtering scenes by analyzed status."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?analyzed=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_scenes_filter_by_video_analyzed(self, client, mock_db):
        """Test filtering scenes by video analyzed status."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?video_analyzed=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_scenes_filter_by_date_range(self, client, mock_db, mock_scene):
        """Test filtering scenes by date range."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get(
            "/api/scenes/?date_from=2024-01-01T00:00:00Z&date_to=2024-12-31T23:59:59Z"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_filter_multiple_performers(self, client, mock_db, mock_scene):
        """Test filtering scenes by multiple performer IDs."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?performer_ids=perf1&performer_ids=perf2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_filter_multiple_tags(self, client, mock_db, mock_scene):
        """Test filtering scenes by multiple tag IDs."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get("/api/scenes/?tag_ids=tag1&tag_ids=tag2&tag_ids=tag3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_complex_filters(self, client, mock_db, mock_scene):
        """Test combining multiple filters."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[mock_scene])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        response = client.get(
            "/api/scenes/?search=test&organized=true&analyzed=false&"
            "performer_ids=perf1&tag_ids=tag1&studio_id=studio1"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_scenes_invalid_date_format(self, client, mock_db):
        """Test filtering scenes with invalid date format."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        # Invalid date format should be ignored
        response = client.get("/api/scenes/?date_from=invalid-date")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_scenes_sort_by_multiple_fields(self, client, mock_db):
        """Test sorting scenes by different fields."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        # Test sort by stash_date descending
        response = client.get("/api/scenes/?sort_by=stash_date&sort_order=desc")

        assert response.status_code == 200

    def test_list_scenes_empty_filter_arrays(self, client, mock_db):
        """Test with empty arrays for performer and tag filters."""
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0

        # Mock scene query
        mock_scene_result = Mock()
        mock_scalars = Mock()
        mock_unique = Mock()
        mock_all = Mock(return_value=[])
        mock_unique.all = mock_all
        mock_scalars.unique.return_value = mock_unique
        mock_scene_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_scene_result])

        # Empty arrays should be treated as no filter
        response = client.get("/api/scenes/?performer_ids=&tag_ids=")

        assert response.status_code == 200

    def test_remove_tags_from_scenes_success(self, client, mock_db, mock_sync_service):
        """Test successful removal of tags from scenes."""
        # Create mock tags with string IDs
        mock_tag1 = Mock()
        mock_tag1.id = "322"
        mock_tag1.name = "Tag to Remove"

        mock_tag2 = Mock()
        mock_tag2.id = "323"
        mock_tag2.name = "Tag to Keep"

        # Create mock scene with both tags
        mock_scene = Mock()
        mock_scene.id = "26804"
        mock_scene.tags = [mock_tag1, mock_tag2]

        # Mock database queries
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.all.return_value = [mock_scene]

        mock_db.execute = AsyncMock(return_value=mock_scenes_result)
        mock_db.commit = AsyncMock()

        # Mock stash service
        mock_sync_service.stash_service.update_scene = AsyncMock()

        # Make request with integer IDs (as sent from frontend)
        response = client.post(
            "/api/scenes/remove-tags", json={"scene_ids": [26804], "tag_ids": [322]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["scenes_updated"] == 1
        assert data["tags_affected"] == 1
        assert "Successfully removed" in data["message"]

        # Verify tag was removed from scene
        assert len(mock_scene.tags) == 1
        assert mock_scene.tags[0].id == "323"

        # Verify Stash was updated
        mock_sync_service.stash_service.update_scene.assert_called_once()

    def test_add_tags_to_scenes_success(self, client, mock_db, mock_sync_service):
        """Test successful addition of tags to scenes."""
        # Create mock existing tag
        mock_existing_tag = Mock()
        mock_existing_tag.id = "100"
        mock_existing_tag.name = "Existing Tag"

        # Create mock new tag to add
        mock_new_tag = Mock()
        mock_new_tag.id = "322"
        mock_new_tag.name = "New Tag"

        # Create mock scene with one existing tag
        mock_scene = Mock()
        mock_scene.id = "26804"
        mock_scene.tags = [mock_existing_tag]

        # Mock database queries for scenes
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.all.return_value = [mock_scene]

        # Mock database queries for tags
        mock_tags_result = Mock()
        mock_tags_result.scalars.return_value.all.return_value = [mock_new_tag]

        # Configure db.execute to return appropriate results
        async def mock_execute(query):
            query_str = str(query)
            if "scene" in query_str.lower():
                return mock_scenes_result
            else:  # tag query
                return mock_tags_result

        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.commit = AsyncMock()

        # Mock stash service
        mock_sync_service.stash_service.update_scene = AsyncMock()

        # Make request with integer IDs (as sent from frontend)
        response = client.post(
            "/api/scenes/add-tags", json={"scene_ids": [26804], "tag_ids": [322]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["scenes_updated"] == 1
        assert data["tags_affected"] == 1
        assert "Successfully added" in data["message"]

        # Verify tag was added to scene
        assert len(mock_scene.tags) == 2

        # Verify Stash was updated
        mock_sync_service.stash_service.update_scene.assert_called_once()

    def test_remove_tags_no_scenes_found(self, client, mock_db, mock_sync_service):
        """Test removing tags when no scenes are found."""
        # Mock empty scenes result
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(return_value=mock_scenes_result)

        # Make request
        response = client.post(
            "/api/scenes/remove-tags", json={"scene_ids": [99999], "tag_ids": [322]}
        )

        assert response.status_code == 404
        assert "No scenes found" in response.json()["detail"]

    def test_add_tags_no_tags_found(self, client, mock_db, mock_sync_service):
        """Test adding tags when no tags are found."""
        # Create mock scene
        mock_scene = Mock()
        mock_scene.id = "26804"
        mock_scene.tags = []

        # Mock database queries for scenes
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.all.return_value = [mock_scene]

        # Mock empty tags result
        mock_tags_result = Mock()
        mock_tags_result.scalars.return_value.all.return_value = []

        # Configure db.execute to return appropriate results
        async def mock_execute(query):
            query_str = str(query)
            if "scene" in query_str.lower():
                return mock_scenes_result
            else:  # tag query
                return mock_tags_result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # Make request
        response = client.post(
            "/api/scenes/add-tags", json={"scene_ids": [26804], "tag_ids": [99999]}
        )

        assert response.status_code == 404
        assert "No tags found" in response.json()["detail"]

    def test_remove_tags_no_changes_needed(self, client, mock_db, mock_sync_service):
        """Test removing tags that aren't on the scene."""
        # Create mock tag
        mock_tag = Mock()
        mock_tag.id = "100"
        mock_tag.name = "Existing Tag"

        # Create mock scene with one tag
        mock_scene = Mock()
        mock_scene.id = "26804"
        mock_scene.tags = [mock_tag]

        # Mock database queries
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.all.return_value = [mock_scene]

        mock_db.execute = AsyncMock(return_value=mock_scenes_result)
        mock_db.commit = AsyncMock()

        # Mock stash service
        mock_sync_service.stash_service.update_scene = AsyncMock()

        # Try to remove a tag that doesn't exist on the scene
        response = client.post(
            "/api/scenes/remove-tags",
            json={"scene_ids": [26804], "tag_ids": [999]},  # Non-existent tag
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["scenes_updated"] == 0  # No scenes should be updated
        assert data["tags_affected"] == 1

        # Verify no changes were made
        assert len(mock_scene.tags) == 1
        assert mock_scene.tags[0].id == "100"

        # Verify Stash was NOT called since no changes
        mock_sync_service.stash_service.update_scene.assert_not_called()

    def test_bulk_tag_operations_multiple_scenes(
        self, client, mock_db, mock_sync_service
    ):
        """Test tag operations on multiple scenes."""
        # Create mock tags
        mock_tag = Mock()
        mock_tag.id = "322"
        mock_tag.name = "Tag to Remove"

        # Create multiple mock scenes
        mock_scene1 = Mock()
        mock_scene1.id = "1001"
        mock_scene1.tags = [mock_tag]

        mock_scene2 = Mock()
        mock_scene2.id = "1002"
        mock_scene2.tags = [mock_tag]

        # Mock database queries
        mock_scenes_result = Mock()
        mock_scenes_result.scalars.return_value.all.return_value = [
            mock_scene1,
            mock_scene2,
        ]

        mock_db.execute = AsyncMock(return_value=mock_scenes_result)
        mock_db.commit = AsyncMock()

        # Mock stash service
        mock_sync_service.stash_service.update_scene = AsyncMock()

        # Remove tag from multiple scenes
        response = client.post(
            "/api/scenes/remove-tags",
            json={"scene_ids": [1001, 1002], "tag_ids": [322]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["scenes_updated"] == 2  # Both scenes should be updated
        assert data["tags_affected"] == 1

        # Verify tags were removed from both scenes
        assert len(mock_scene1.tags) == 0
        assert len(mock_scene2.tags) == 0

        # Verify Stash was called for both scenes
        assert mock_sync_service.stash_service.update_scene.call_count == 2
