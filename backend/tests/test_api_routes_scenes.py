"""Tests for scene API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.scene import Scene


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
    scene.id = str(uuid4())
    scene.title = "Test Scene"
    scene.paths = ["/path/to/scene.mp4"]  # Changed from path to paths
    scene.file_path = "/actual/path/to/scene.mp4"
    scene.details = "Scene details"
    scene.rating = 5
    scene.duration = 3600
    scene.organized = True
    scene.analyzed = False
    scene.stash_created_at = datetime.utcnow()
    scene.stash_updated_at = datetime.utcnow()
    scene.stash_date = datetime.utcnow()
    scene.created_at = datetime.utcnow()
    scene.updated_at = datetime.utcnow()
    scene.last_synced = datetime.utcnow()
    scene.id = "stash123"
    scene.performers = []
    scene.tags = []
    scene.studio = None
    scene.markers = []
    # Metadata fields
    scene.size = 1024000000
    scene.width = 1920
    scene.height = 1080
    scene.framerate = 30.0
    scene.bitrate = 5000
    scene.codec = "h264"
    scene.video_analyzed = False
    scene.to_dict = Mock(
        return_value={
            "id": scene.id,
            "title": scene.title,
            "paths": scene.paths,
            "file_path": scene.file_path,
            "details": scene.details,
            "rating": scene.rating,
            "duration": scene.duration,
            "organized": scene.organized,
            "analyzed": scene.analyzed,
            "stash_created_at": scene.stash_created_at,
            "stash_updated_at": scene.stash_updated_at,
            "stash_date": scene.stash_date,
            "last_synced": scene.last_synced,
            "performers": [],
            "tags": [],
            "studio": None,
            "markers": [],
            # Metadata fields
            "size": scene.size,
            "width": scene.width,
            "height": scene.height,
            "framerate": scene.framerate,
            "bitrate": scene.bitrate,
            "video_codec": scene.codec,
            "video_analyzed": scene.video_analyzed,
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

        mock_scene = Mock(
            spec=Scene,
            id="123",
            title="Test Scene",
            paths=["/path/to/scene.mp4"],
            file_path="/actual/path/to/scene.mp4",
            organized=True,
            analyzed=False,
            details="Scene details",
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            stash_date=datetime.utcnow(),
            last_synced=datetime.utcnow(),
            studio=mock_studio,
            performers=[mock_performer],
            tags=[mock_tag],
            # Metadata fields
            duration=1800.5,
            size=1024000000,
            width=1920,
            height=1080,
            framerate=30.0,
            bitrate=5000,
            codec="h264",
            video_analyzed=False,
            markers=[],
        )

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

        mock_scene = Mock(
            spec=Scene,
            id="1",
            title="Test Scene",
            paths=["/path/to/scene.mp4"],
            file_path="/actual/path/to/scene.mp4",
            organized=True,
            analyzed=False,
            details="Scene details",
            stash_created_at=datetime.utcnow(),
            stash_updated_at=datetime.utcnow(),
            stash_date=datetime.utcnow(),
            last_synced=datetime.utcnow(),
            studio=mock_studio,
            performers=[],
            tags=[],
            # Metadata fields
            duration=1800.5,
            size=1024000000,
            width=1920,
            height=1080,
            framerate=30.0,
            bitrate=5000,
            codec="h264",
            video_analyzed=False,
            markers=[],
        )

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
