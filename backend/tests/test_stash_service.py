"""Tests for Stash service."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.services.stash import (
    StashAuthenticationError,
    StashConnectionError,
    StashGraphQLError,
    StashRateLimitError,
)
from app.services.stash_service import StashService


class TestStashService:
    """Test Stash service functionality."""

    @pytest.fixture
    def stash_service(self):
        """Create Stash service instance."""
        return StashService(
            stash_url="http://localhost:9999",
            api_key="test_api_key",
            timeout=30,
            max_retries=3,
        )

    def test_initialization(self):
        """Test service initialization."""
        service = StashService(stash_url="http://localhost:9999/", api_key="test_key")

        assert service.base_url == "http://localhost:9999"
        assert service.graphql_url == "http://localhost:9999/graphql"
        assert service.api_key == "test_key"
        assert service.timeout == 30
        assert service.max_retries == 3

    @pytest.mark.asyncio
    async def testexecute_graphql_success(self, stash_service):
        """Test successful GraphQL query execution."""
        query = "query { findScenes { scenes { id title } } }"
        variables = {"filter": {"per_page": 10}}
        expected_response = {
            "data": {
                "findScenes": {
                    "scenes": [
                        {"id": "1", "title": "Scene 1"},
                        {"id": "2", "title": "Scene 2"},
                    ]
                }
            }
        }

        # Mock the HTTP client
        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_response.headers = {}
            mock_post.return_value = mock_response

            result = await stash_service.execute_graphql(query, variables)

            assert result == expected_response["data"]
            mock_post.assert_called_once_with(
                stash_service.graphql_url, json={"query": query, "variables": variables}
            )

    @pytest.mark.asyncio
    async def test_execute_graphql_graphql_error(self, stash_service):
        """Test GraphQL error handling."""
        query = "query { invalidQuery }"
        error_response = {"errors": [{"message": "Field 'invalidQuery' not found"}]}

        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = error_response
            mock_response.headers = {}
            mock_post.return_value = mock_response

            with pytest.raises(
                StashGraphQLError, match="Field 'invalidQuery' not found"
            ):
                await stash_service.execute_graphql(query)

    @pytest.mark.asyncio
    async def testexecute_graphql_connection_error(self, stash_service):
        """Test connection error handling."""
        query = "query { findScenes { scenes { id } } }"

        with patch.object(stash_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(StashConnectionError, match="Failed to connect"):
                await stash_service.execute_graphql(query)

    @pytest.mark.asyncio
    async def testexecute_graphql_authentication_error(self, stash_service):
        """Test authentication error handling."""
        query = "query { findScenes { scenes { id } } }"

        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "Unauthorized"}
            mock_response.headers = {}
            mock_post.return_value = mock_response

            with pytest.raises(StashAuthenticationError):
                await stash_service.execute_graphql(query)

    @pytest.mark.asyncio
    async def testexecute_graphql_rate_limit(self, stash_service):
        """Test rate limit error handling."""
        query = "query { findScenes { scenes { id } } }"

        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.json.return_value = {"error": "Rate limit exceeded"}
            mock_response.headers = {"Retry-After": "60"}
            mock_post.return_value = mock_response

            with pytest.raises(StashRateLimitError) as exc_info:
                await stash_service.execute_graphql(query)

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_find_scenes(self, stash_service):
        """Test finding scenes."""
        scenes_data = [
            {"id": "1", "title": "Scene 1", "path": "/path/1"},
            {"id": "2", "title": "Scene 2", "path": "/path/2"},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findScenes": {"count": 2, "scenes": scenes_data}
            }

            result = await stash_service.find_scenes(per_page=10, page=1)

            assert result["count"] == 2
            assert len(result["scenes"]) == 2
            assert result["scenes"][0]["title"] == "Scene 1"

    @pytest.mark.asyncio
    async def test_get_scene(self, stash_service):
        """Test getting a single scene."""
        scene_id = "123"
        scene_data = {
            "id": scene_id,
            "title": "Test Scene",
            "path": "/path/to/scene.mp4",
            "performers": [],
            "tags": [],
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findScene": scene_data}

            result = await stash_service.get_scene(scene_id)

            assert result["id"] == scene_id
            assert result["title"] == "Test Scene"

    @pytest.mark.asyncio
    async def test_update_scene(self, stash_service):
        """Test updating a scene."""
        scene_id = "123"
        update_data = {"title": "Updated Title", "details": "New details"}

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"sceneUpdate": {"id": scene_id, **update_data}}

            result = await stash_service.update_scene(scene_id, update_data)

            assert result["id"] == scene_id
            assert result["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_find_performers(self, stash_service):
        """Test finding performers."""
        performers_data = [
            {"id": "1", "name": "Performer 1"},
            {"id": "2", "name": "Performer 2"},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findPerformers": {"count": 2, "performers": performers_data}
            }

            result = await stash_service.find_performers(
                filter={"name": {"value": "Performer"}}
            )

            assert result["count"] == 2
            assert len(result["performers"]) == 2

    @pytest.mark.asyncio
    async def test_create_tag(self, stash_service):
        """Test creating a tag."""
        tag_name = "New Tag"

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "tagCreate": {"id": "tag123", "name": tag_name}
            }

            result = await stash_service.create_tag(tag_name)

            assert result["id"] == "tag123"
            assert result["name"] == tag_name

    @pytest.mark.asyncio
    async def test_batch_update_scenes(self, stash_service):
        """Test batch updating scenes."""
        scene_ids = ["1", "2", "3"]
        update_data = {"studio_id": "studio123"}

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            # Mock bulk update response
            mock_execute.return_value = {
                "bulkSceneUpdate": [{"id": scene_id} for scene_id in scene_ids]
            }

            results = await stash_service.batch_update_scenes(scene_ids, update_data)

            assert len(results) == 3
            assert all(r["id"] in scene_ids for r in results)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, stash_service):
        """Test successful connection test."""
        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"version": {"version": "v0.20.0"}}

            result = await stash_service.test_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, stash_service):
        """Test failed connection test."""
        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.side_effect = StashConnectionError("Connection failed")

            result = await stash_service.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, stash_service):
        """Test retry mechanism on rate limit."""
        query = "query { findScenes { scenes { id } } }"

        # Reduce retry delay for testing
        stash_service.max_retries = 2

        with patch.object(stash_service._client, "post") as mock_post:
            # First call: rate limit
            # Second call: success
            mock_response_rate_limit = Mock()
            mock_response_rate_limit.status_code = 429
            mock_response_rate_limit.json.return_value = {"error": "Rate limit"}
            mock_response_rate_limit.headers = {"Retry-After": "1"}

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": {"result": "success"}}
            mock_response_success.headers = {}

            mock_post.side_effect = [mock_response_rate_limit, mock_response_success]

            # Patch sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await stash_service.execute_graphql(query)

                assert result == {"result": "success"}
                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_close(self, stash_service):
        """Test closing the service."""
        with patch.object(stash_service._client, "aclose") as mock_aclose:
            await stash_service.close()
            mock_aclose.assert_called_once()
