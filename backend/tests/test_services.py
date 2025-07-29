"""Tests for service layer to improve coverage."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.core.config import Settings
from app.models.job import JobStatus, JobType
from app.services.job_service import JobService
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService
from app.services.websocket_manager import WebSocketManager


class TestJobService:
    """Test JobService functionality."""

    @pytest.fixture
    def job_service(self):
        """Create JobService instance."""
        return JobService()

    @pytest.mark.asyncio
    async def test_create_job(self, job_service):
        """Test creating a new job."""
        mock_db = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_job = Mock(id="job123", type=JobType.SYNC, job_metadata={})

        # Register a mock handler for SYNC job type
        mock_handler = AsyncMock(return_value={"status": "success"})
        job_service.register_handler(JobType.SYNC, mock_handler)

        # Mock dependencies
        with (
            patch("app.services.job_service.job_repository") as mock_repo,
            patch("app.services.job_service.get_task_queue") as mock_get_queue,
            patch("app.services.job_service.uuid.uuid4", return_value="job123"),
            patch("app.services.job_service.websocket_manager") as mock_ws,
        ):

            mock_repo.create_job = AsyncMock(return_value=mock_job)
            mock_repo.update_job_status = AsyncMock()
            mock_queue = Mock()
            mock_queue.submit = AsyncMock(return_value="task123")
            mock_get_queue.return_value = mock_queue
            mock_ws.broadcast = AsyncMock()

            job = await job_service.create_job(
                job_type=JobType.SYNC, db=mock_db, metadata={"target": "scenes"}
            )

            assert job.id == "job123"
            mock_repo.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job(self, job_service):
        """Test getting a job by ID."""
        mock_job = Mock(id="job123", status=JobStatus.RUNNING)
        mock_db = Mock()

        with patch("app.services.job_service.job_repository") as mock_repo:
            mock_repo.get_job = AsyncMock(return_value=mock_job)

            job = await job_service.get_job("job123", mock_db)

            assert job == mock_job
            mock_repo.get_job.assert_called_once_with("job123", mock_db)

    # Methods update_progress, complete_job, fail_job don't exist in JobService

    @pytest.mark.asyncio
    async def test_cancel_job(self, job_service):
        """Test canceling a job."""
        mock_job = Mock(
            id="job123", status=JobStatus.RUNNING, job_metadata={"task_id": "task123"}
        )
        mock_db = Mock()

        with (
            patch("app.services.job_service.job_repository") as mock_repo,
            patch("app.services.job_service.get_task_queue") as mock_get_queue,
            patch("app.services.job_service.websocket_manager") as mock_ws,
        ):

            mock_repo.get_job = AsyncMock(return_value=mock_job)
            mock_repo.cancel_job = AsyncMock(return_value=mock_job)
            mock_repo._fetch_job = AsyncMock(return_value=mock_job)
            mock_repo.update_job_status = AsyncMock()
            mock_queue = Mock()
            mock_queue.cancel_task = AsyncMock()
            mock_get_queue.return_value = mock_queue
            mock_ws.broadcast_json = AsyncMock()
            mock_ws.broadcast_job_update = AsyncMock()

            result = await job_service.cancel_job("job123", mock_db)

            assert result is True
            mock_repo.get_job.assert_called_once_with("job123", mock_db)
            mock_repo.update_job_status.assert_called_once_with(
                job_id="job123",
                status=JobStatus.CANCELLING,
                db=mock_db,
                message="Cancellation requested",
            )
            mock_queue.cancel_task.assert_called_once_with("task123")

    # retry_job method doesn't exist in JobService


class TestStashService:
    """Test StashService functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        # Create a mock StashSettings object
        stash_settings = Mock()
        stash_settings.url = "http://localhost:9999"
        stash_settings.api_key = "test-key"
        settings.stash = stash_settings
        return settings

    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def stash_service(self, mock_settings, mock_client):
        """Create StashService instance."""
        service = StashService(
            stash_url=mock_settings.stash.url, api_key=mock_settings.stash.api_key
        )
        service._client = mock_client
        return service

    @pytest.mark.asyncio
    async def test_get_scene(self, stash_service, mock_client):
        """Test getting a scene from Stash."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "findScene": {
                    "id": "123",
                    "title": "Test Scene",
                    "path": "/path/to/scene.mp4",
                }
            }
        }
        mock_client.post.return_value = mock_response

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findScene": {
                    "id": "123",
                    "title": "Test Scene",
                    "paths": [{"path": "/path/to/scene.mp4"}],
                    "organized": False,
                    "o_counter": 0,
                    "rating100": None,
                    "details": None,
                    "date": None,
                    "created_at": None,
                    "updated_at": None,
                    "studio": None,
                    "performers": [],
                    "tags": [],
                    "file": None,
                    "galleries": [],
                    "movies": [],
                    "interactive": False,
                    "interactive_speed": None,
                }
            }

            scene = await stash_service.get_scene("123")

            assert scene["id"] == "123"
            assert scene["title"] == "Test Scene"
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_scenes(self, stash_service, mock_client):
        """Test finding scenes with filters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "findScenes": {
                    "scenes": [
                        {"id": "1", "title": "Scene 1"},
                        {"id": "2", "title": "Scene 2"},
                    ],
                    "count": 2,
                }
            }
        }
        mock_client.post.return_value = mock_response

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findScenes": {
                    "scenes": [
                        {
                            "id": "1",
                            "title": "Scene 1",
                            "paths": [],
                            "organized": False,
                            "o_counter": 0,
                            "rating100": None,
                            "details": None,
                            "date": None,
                            "created_at": None,
                            "updated_at": None,
                            "studio": None,
                            "performers": [],
                            "tags": [],
                            "file": None,
                            "galleries": [],
                            "movies": [],
                            "interactive": False,
                            "interactive_speed": None,
                        },
                        {
                            "id": "2",
                            "title": "Scene 2",
                            "paths": [],
                            "organized": False,
                            "o_counter": 0,
                            "rating100": None,
                            "details": None,
                            "date": None,
                            "created_at": None,
                            "updated_at": None,
                            "studio": None,
                            "performers": [],
                            "tags": [],
                            "file": None,
                            "galleries": [],
                            "movies": [],
                            "interactive": False,
                            "interactive_speed": None,
                        },
                    ],
                    "count": 2,
                }
            }

            result = await stash_service.find_scenes(query="test", page=1, per_page=10)

            assert result["count"] == 2
            assert len(result["scenes"]) == 2
            assert result["scenes"][0]["id"] == "1"
            assert result["scenes"][1]["id"] == "2"

    @pytest.mark.asyncio
    async def test_update_scene(self, stash_service, mock_client):
        """Test updating a scene."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"sceneUpdate": {"id": "123", "title": "Updated Title"}}
        }
        mock_client.post.return_value = mock_response

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "sceneUpdate": {
                    "id": "123",
                    "title": "Updated Title",
                    "paths": [],
                    "organized": False,
                    "o_counter": 0,
                    "rating100": 90,
                    "details": None,
                    "date": None,
                    "created_at": None,
                    "updated_at": None,
                    "studio": None,
                    "performers": [],
                    "tags": [],
                    "file": None,
                    "galleries": [],
                    "movies": [],
                    "interactive": False,
                    "interactive_speed": None,
                }
            }

            updates = {"title": "Updated Title", "rating": 90}
            result = await stash_service.update_scene("123", updates)

            assert result["id"] == "123"
            assert result["title"] == "Updated Title"
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_performers(self, stash_service, mock_client):
        """Test getting performers."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "allPerformers": [
                    {"id": "p1", "name": "Performer 1"},
                    {"id": "p2", "name": "Performer 2"},
                ]
            }
        }
        mock_client.post.return_value = mock_response

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "allPerformers": [
                    {
                        "id": "p1",
                        "name": "Performer 1",
                        "image_path": None,
                        "birthdate": None,
                        "ethnicity": None,
                        "country": None,
                        "eye_color": None,
                        "height_cm": None,
                        "measurements": None,
                        "fake_tits": None,
                        "career_length": None,
                        "tattoos": None,
                        "piercings": None,
                        "aliases": None,
                        "favorite": False,
                        "tags": [],
                        "ignore_auto_tag": False,
                        "gender": None,
                        "url": None,
                        "twitter": None,
                        "instagram": None,
                        "created_at": None,
                        "updated_at": None,
                        "rating100": None,
                        "details": None,
                        "death_date": None,
                        "hair_color": None,
                        "weight": None,
                        "penis_length": None,
                        "circumcised": None,
                    },
                    {
                        "id": "p2",
                        "name": "Performer 2",
                        "image_path": None,
                        "birthdate": None,
                        "ethnicity": None,
                        "country": None,
                        "eye_color": None,
                        "height_cm": None,
                        "measurements": None,
                        "fake_tits": None,
                        "career_length": None,
                        "tattoos": None,
                        "piercings": None,
                        "aliases": None,
                        "favorite": False,
                        "tags": [],
                        "ignore_auto_tag": False,
                        "gender": None,
                        "url": None,
                        "twitter": None,
                        "instagram": None,
                        "created_at": None,
                        "updated_at": None,
                        "rating100": None,
                        "details": None,
                        "death_date": None,
                        "hair_color": None,
                        "weight": None,
                        "penis_length": None,
                        "circumcised": None,
                    },
                ]
            }

            # Mock the cache to avoid the KeyError
            with patch.object(stash_service._entity_cache, "set_performers"):
                result = await stash_service.get_all_performers()

            assert len(result) == 2
            assert result[0]["id"] == "p1"
            assert result[1]["id"] == "p2"

    @pytest.mark.asyncio
    async def test_handle_graphql_error(self, stash_service, mock_client):
        """Test handling GraphQL errors."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Scene not found", "path": ["findScene"]}]
        }
        mock_client.post.return_value = mock_response

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.side_effect = Exception("GraphQL error: Scene not found")

            with pytest.raises(Exception, match="Scene not found"):
                await stash_service.get_scene("nonexistent")

    @pytest.mark.asyncio
    async def test_connection_error(self, stash_service, mock_client):
        """Test handling connection errors."""
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(Exception, match="Connection refused"):
                await stash_service.get_scene("123")

    @pytest.mark.asyncio
    async def test_get_stats(self, stash_service):
        """Test getting Stash statistics."""
        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "stats": {
                    "scene_count": 1000,
                    "performer_count": 200,
                    "tag_count": 500,
                    "studio_count": 50,
                }
            }

            stats = await stash_service.get_stats()

            assert stats["scene_count"] == 1000
            assert stats["performer_count"] == 200


class TestOpenAIClient:
    """Test OpenAIClient functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.openai_api_key = "test-key"
        settings.openai_model = "gpt-4"
        return settings

    @pytest.fixture
    def openai_client(self, mock_settings):
        """Create OpenAIClient instance."""
        return OpenAIClient(api_key=mock_settings.openai_api_key)

    # analyze_scene method doesn't exist in OpenAIClient

    # generate_description method doesn't exist in OpenAIClient


class TestWebSocketManager:
    """Test WebSocketManager functionality."""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocketManager instance."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_connect_client(self, ws_manager):
        """Test connecting a WebSocket client."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        await ws_manager.connect(mock_websocket)

        assert mock_websocket in ws_manager.active_connections
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_client(self, ws_manager):
        """Test disconnecting a WebSocket client."""
        mock_websocket = AsyncMock()

        ws_manager.active_connections = [mock_websocket]
        await ws_manager.disconnect(mock_websocket)

        assert mock_websocket not in ws_manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_message(self, ws_manager):
        """Test broadcasting message to all clients."""
        # Create mock websockets
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        # Set up the client_state attribute
        from starlette.websockets import WebSocketState

        mock_ws1.client_state = WebSocketState.CONNECTED
        mock_ws2.client_state = WebSocketState.CONNECTED

        ws_manager.active_connections = [mock_ws1, mock_ws2]

        message = {"type": "update", "data": "test"}
        await ws_manager.broadcast_json(message)

        # Verify successful sends - broadcast_json converts to JSON string
        import json

        expected_message = json.dumps(message)
        mock_ws1.send_text.assert_called_with(expected_message)
        mock_ws2.send_text.assert_called_with(expected_message)

    # send_to_client method doesn't exist in WebSocketManager

    # send_to_client method doesn't exist in WebSocketManager

    # get_connected_clients method doesn't exist in WebSocketManager
