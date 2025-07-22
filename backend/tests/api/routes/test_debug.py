"""
Tests for debug API routes.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.dependencies import get_stash_service
from app.main import app
from app.services.stash_service import StashService


@pytest.fixture
def mock_stash_service():
    """Create mock stash service."""
    service = AsyncMock(spec=StashService)
    return service


@pytest.fixture
def test_client_with_mock_stash(mock_stash_service):
    """Create test client with mocked stash service."""
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_service

    with TestClient(app) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


class TestDebugRoutes:
    """Test debug API routes."""

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_success(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test successful retrieval of scene debug data."""
        # Mock the GraphQL response
        mock_response = {
            "findScenes": {
                "count": 1,
                "scenes": [
                    {
                        "id": "123",
                        "title": "Test Scene",
                        "details": "Test details",
                        "date": "2023-01-01",
                        "rating100": 80,
                        "organized": True,
                        "interactive": False,
                        "interactive_speed": None,
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                        "o_counter": 5,
                        "paths": {
                            "screenshot": "/path/to/screenshot.jpg",
                            "preview": "/path/to/preview.mp4",
                            "stream": "/path/to/stream.mp4",
                            "webp": "/path/to/webp.webp",
                            "vtt": "/path/to/vtt.vtt",
                            "sprite": "/path/to/sprite.jpg",
                            "funscript": None,
                            "interactive_heatmap": None,
                            "caption": None,
                        },
                        "studio": {"id": "1", "name": "Test Studio"},
                        "performers": [
                            {
                                "id": "1",
                                "name": "Test Performer",
                                "gender": "FEMALE",
                                "favorite": True,
                                "rating100": 90,
                            }
                        ],
                        "tags": [{"id": "1", "name": "Test Tag"}],
                        "movies": [],
                        "galleries": [
                            {
                                "id": "1",
                                "title": "Test Gallery",
                                "paths": {
                                    "cover": "/path/to/cover.jpg",
                                    "preview": "/path/to/gallery_preview.jpg",
                                },
                            }
                        ],
                        "files": [
                            {
                                "id": "1",
                                "path": "/path/to/video.mp4",
                                "size": 1024000000,
                                "duration": 1800.5,
                                "video_codec": "h264",
                                "audio_codec": "aac",
                                "width": 1920,
                                "height": 1080,
                                "frame_rate": 30.0,
                                "bit_rate": 5000000,
                                "fingerprints": [
                                    {"type": "phash", "value": "abcdef123456"}
                                ],
                            }
                        ],
                    }
                ],
            }
        }

        mock_stash_service.execute_graphql.return_value = mock_response

        response = test_client_with_mock_stash.get("/api/debug/stashscene/123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "query" in data
        assert "result" in data

        # Verify query contains the scene ID
        assert "findScenes" in data["query"]
        assert "findScenes(scene_ids: [123])" in data["query"]

        # Verify result
        assert data["result"] == mock_response

        # Verify the GraphQL call
        mock_stash_service.execute_graphql.assert_called_once()
        call_args = mock_stash_service.execute_graphql.call_args
        assert call_args[0][1] == {"scene_ids": [123]}

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_not_found(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test retrieval of non-existent scene."""
        # Mock empty response
        mock_response = {"findScenes": {"count": 0, "scenes": []}}

        mock_stash_service.execute_graphql.return_value = mock_response

        response = test_client_with_mock_stash.get("/api/debug/stashscene/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Scene 999 not found in Stash" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_invalid_id(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test with invalid scene ID."""
        response = test_client_with_mock_stash.get("/api/debug/stashscene/invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid scene ID: invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_graphql_error(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test handling of GraphQL errors."""
        mock_stash_service.execute_graphql.side_effect = Exception(
            "GraphQL connection error"
        )

        response = test_client_with_mock_stash.get("/api/debug/stashscene/123")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to fetch scene from Stash" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_missing_data(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test handling of response with missing data."""
        # Mock response with missing findScenes
        mock_response = {}

        mock_stash_service.execute_graphql.return_value = mock_response

        response = test_client_with_mock_stash.get("/api/debug/stashscene/123")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_null_scenes(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test handling of null scenes in response."""
        # Mock response with null scenes
        mock_response = {"findScenes": {"count": 0, "scenes": None}}

        mock_stash_service.execute_graphql.return_value = mock_response

        response = test_client_with_mock_stash.get("/api/debug/stashscene/123")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_large_id(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test with a very large scene ID."""
        large_id = "9999999999"

        mock_response = {
            "findScenes": {
                "count": 1,
                "scenes": [
                    {
                        "id": large_id,
                        "title": "Scene with large ID",
                        "details": None,
                        "date": None,
                        "rating100": None,
                        "organized": False,
                        "interactive": False,
                        "interactive_speed": None,
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                        "o_counter": 0,
                        "paths": {
                            "screenshot": None,
                            "preview": None,
                            "stream": None,
                            "webp": None,
                            "vtt": None,
                            "sprite": None,
                            "funscript": None,
                            "interactive_heatmap": None,
                            "caption": None,
                        },
                        "studio": None,
                        "performers": [],
                        "tags": [],
                        "movies": [],
                        "galleries": [],
                        "files": [],
                    }
                ],
            }
        }

        mock_stash_service.execute_graphql.return_value = mock_response

        response = test_client_with_mock_stash.get(f"/api/debug/stashscene/{large_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"]["findScenes"]["scenes"][0]["id"] == large_id

    @pytest.mark.asyncio
    async def test_get_stash_scene_debug_complex_scene(
        self, test_client_with_mock_stash: TestClient, mock_stash_service: AsyncMock
    ):
        """Test with a scene containing complex nested data."""
        mock_response = {
            "findScenes": {
                "count": 1,
                "scenes": [
                    {
                        "id": "456",
                        "title": "Complex Scene",
                        "details": "Detailed description with special chars: !@#$%^&*()",
                        "date": "2023-12-25",
                        "rating100": 100,
                        "organized": True,
                        "interactive": True,
                        "interactive_speed": 2,
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-12-25T23:59:59",
                        "o_counter": 100,
                        "paths": {
                            "screenshot": "/path/screenshot.jpg",
                            "preview": "/path/preview.mp4",
                            "stream": "/path/stream.m3u8",
                            "webp": "/path/webp.webp",
                            "vtt": "/path/vtt.vtt",
                            "sprite": "/path/sprite.jpg",
                            "funscript": "/path/funscript.json",
                            "interactive_heatmap": "/path/heatmap.png",
                            "caption": "/path/caption.srt",
                        },
                        "studio": {"id": "10", "name": "Studio with & Special Chars"},
                        "performers": [
                            {
                                "id": "20",
                                "name": "Performer One",
                                "gender": "MALE",
                                "favorite": False,
                                "rating100": 75,
                            },
                            {
                                "id": "21",
                                "name": "Performer Two",
                                "gender": "FEMALE",
                                "favorite": True,
                                "rating100": 95,
                            },
                            {
                                "id": "22",
                                "name": "Performer Three",
                                "gender": "TRANSGENDER_MALE",
                                "favorite": False,
                                "rating100": None,
                            },
                        ],
                        "tags": [
                            {"id": "30", "name": "Tag One"},
                            {"id": "31", "name": "Tag/With/Slashes"},
                            {"id": "32", "name": "Tag-With-Dashes"},
                        ],
                        "movies": [
                            {
                                "movie": {
                                    "id": "40",
                                    "name": "Movie Collection Part 1",
                                },
                                "scene_index": 3,
                            },
                            {
                                "movie": {
                                    "id": "41",
                                    "name": "Movie Collection Part 2",
                                },
                                "scene_index": 1,
                            },
                        ],
                        "galleries": [
                            {
                                "id": "50",
                                "title": "Gallery One",
                                "paths": {
                                    "cover": "/gallery1/cover.jpg",
                                    "preview": "/gallery1/preview.jpg",
                                },
                            },
                            {
                                "id": "51",
                                "title": "Gallery Two",
                                "paths": {
                                    "cover": "/gallery2/cover.jpg",
                                    "preview": None,
                                },
                            },
                        ],
                        "files": [
                            {
                                "id": "60",
                                "path": "/videos/main.mp4",
                                "size": 2147483648,
                                "duration": 3600.25,
                                "video_codec": "h265",
                                "audio_codec": "opus",
                                "width": 3840,
                                "height": 2160,
                                "frame_rate": 60.0,
                                "bit_rate": 8000000,
                                "fingerprints": [
                                    {"type": "phash", "value": "1234567890abcdef"},
                                    {"type": "oshash", "value": "fedcba0987654321"},
                                ],
                            },
                            {
                                "id": "61",
                                "path": "/videos/backup.mkv",
                                "size": 1073741824,
                                "duration": 3600.25,
                                "video_codec": "av1",
                                "audio_codec": "flac",
                                "width": 1920,
                                "height": 1080,
                                "frame_rate": 30.0,
                                "bit_rate": 4000000,
                                "fingerprints": [],
                            },
                        ],
                    }
                ],
            }
        }

        mock_stash_service.execute_graphql.return_value = mock_response

        response = test_client_with_mock_stash.get("/api/debug/stashscene/456")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify complex data is preserved
        scene = data["result"]["findScenes"]["scenes"][0]
        assert len(scene["performers"]) == 3
        assert len(scene["tags"]) == 3
        assert len(scene["movies"]) == 2
        assert len(scene["galleries"]) == 2
        assert len(scene["files"]) == 2
        assert scene["files"][0]["fingerprints"][0]["type"] == "phash"
        assert scene["interactive"] is True
        assert scene["interactive_speed"] == 2
