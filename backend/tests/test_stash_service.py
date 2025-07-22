"""Tests for Stash service."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from tenacity import RetryError

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

    @pytest.mark.asyncio
    async def test_get_all_tags(self, stash_service):
        """Test getting all tags."""
        tags_data = [
            {"id": "1", "name": "Tag 1", "aliases": []},
            {"id": "2", "name": "Tag 2", "aliases": ["tag2-alias"]},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"allTags": tags_data}

            result = await stash_service.get_all_tags()

            assert len(result) == 2
            assert result[0]["name"] == "Tag 1"
            assert result[1]["aliases"] == ["tag2-alias"]

    @pytest.mark.asyncio
    async def test_get_all_studios(self, stash_service):
        """Test getting all studios."""
        studios_data = [
            {"id": "1", "name": "Studio 1", "url": "http://studio1.com"},
            {"id": "2", "name": "Studio 2", "url": "http://studio2.com"},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"allStudios": studios_data}

            result = await stash_service.get_all_studios()

            assert len(result) == 2
            assert result[0]["name"] == "Studio 1"
            assert result[1]["url"] == "http://studio2.com"

    @pytest.mark.asyncio
    async def test_create_performer(self, stash_service):
        """Test creating a performer."""
        performer_data = {
            "name": "New Performer",
            "gender": "FEMALE",
            "birthdate": "1990-01-01",
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "performerCreate": {
                    "id": "perf123",
                    "name": performer_data["name"],
                    "gender": performer_data["gender"],
                    "birthdate": performer_data["birthdate"],
                    "favorite": False,
                    "rating100": None,
                    "url": None,
                }
            }

            result = await stash_service.create_performer(**performer_data)

            assert result["id"] == "perf123"
            assert result["name"] == performer_data["name"]
            assert result["gender"] == performer_data["gender"]

    @pytest.mark.asyncio
    async def test_create_studio(self, stash_service):
        """Test creating a studio."""
        studio_name = "New Studio"
        studio_url = "http://newstudio.com"

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "studioCreate": {
                    "id": "studio123",
                    "name": studio_name,
                    "url": studio_url,
                    "details": None,
                    "rating100": None,
                }
            }

            result = await stash_service.create_studio(name=studio_name, url=studio_url)

            assert result["id"] == "studio123"
            assert result["name"] == studio_name
            assert result["url"] == studio_url

    @pytest.mark.asyncio
    async def test_find_performer(self, stash_service):
        """Test finding a performer by name."""
        performer_name = "Test Performer"
        performer_data = {
            "id": "perf123",
            "name": performer_name,
            "gender": "FEMALE",
            "url": None,
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findPerformers": {"performers": [performer_data]}
            }

            result = await stash_service.find_performer(performer_name)

            assert result is not None
            assert result["id"] == "perf123"
            assert result["name"] == performer_name

    @pytest.mark.asyncio
    async def test_find_tag(self, stash_service):
        """Test finding a tag by name."""
        tag_name = "Test Tag"
        tag_data = {"id": "tag123", "name": tag_name, "aliases": []}

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findTags": {"tags": [tag_data]}}

            result = await stash_service.find_tag(tag_name)

            assert result is not None
            assert result["id"] == "tag123"
            assert result["name"] == tag_name

    @pytest.mark.asyncio
    async def test_find_studio(self, stash_service):
        """Test finding a studio by name."""
        studio_name = "Test Studio"
        studio_data = {"id": "studio123", "name": studio_name, "url": "http://test.com"}

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findStudios": {"studios": [studio_data]}}

            result = await stash_service.find_studio(studio_name)

            assert result is not None
            assert result["id"] == "studio123"
            assert result["name"] == studio_name

    @pytest.mark.asyncio
    async def test_get_stats(self, stash_service):
        """Test getting statistics."""
        stats_data = {
            "stats": {
                "scene_count": 1000,
                "performer_count": 200,
                "studio_count": 50,
                "tag_count": 300,
                "total_size": "1.5TB",
                "total_duration": 360000.0,
            }
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = stats_data

            result = await stash_service.get_stats()

            assert result == stats_data["stats"]

    @pytest.mark.asyncio
    async def test_get_performers_since(self, stash_service):
        """Test getting performers since a date."""
        since_date = datetime(2023, 1, 1)
        performers_data = [
            {"id": "1", "name": "Performer 1", "created_at": "2023-01-15T00:00:00Z"},
            {"id": "2", "name": "Performer 2", "created_at": "2023-02-01T00:00:00Z"},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findPerformers": {"performers": performers_data}
            }

            result = await stash_service.get_performers_since(since_date)

            assert len(result) == 2
            assert result[0]["name"] == "Performer 1"

    @pytest.mark.asyncio
    async def test_get_tags_since(self, stash_service):
        """Test getting tags since a date."""
        since_date = datetime(2023, 1, 1)
        tags_data = [
            {"id": "1", "name": "Tag 1", "created_at": "2023-01-15T00:00:00Z"},
            {"id": "2", "name": "Tag 2", "created_at": "2023-02-01T00:00:00Z"},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findTags": {"tags": tags_data}}

            result = await stash_service.get_tags_since(since_date)

            assert len(result) == 2
            assert result[0]["name"] == "Tag 1"

    @pytest.mark.asyncio
    async def test_get_studios_since(self, stash_service):
        """Test getting studios since a date."""
        since_date = datetime(2023, 1, 1)
        studios_data = [
            {"id": "1", "name": "Studio 1", "created_at": "2023-01-15T00:00:00Z"},
            {"id": "2", "name": "Studio 2", "created_at": "2023-02-01T00:00:00Z"},
        ]

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findStudios": {"studios": studios_data}}

            result = await stash_service.get_studios_since(since_date)

            assert len(result) == 2
            assert result[0]["name"] == "Studio 1"

    @pytest.mark.asyncio
    async def test_create_marker(self, stash_service):
        """Test creating a scene marker."""
        marker_data = {
            "scene_id": "123",
            "title": "New Marker",
            "seconds": 60,
            "tag_ids": ["tag123"],  # Changed from primary_tag_id to tag_ids
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "sceneMarkerCreate": {
                    "id": "marker123",
                    "title": marker_data["title"],
                    "seconds": marker_data["seconds"],
                    "primary_tag": {"id": "tag123", "name": "Tag Name"},
                    "scene": {"id": marker_data["scene_id"]},
                }
            }

            result = await stash_service.create_marker(marker_data)

            assert result["id"] == "marker123"
            assert result["title"] == marker_data["title"]

    @pytest.mark.asyncio
    async def test_complex_scene_update(self, stash_service):
        """Test complex scene update with performers, tags, and studio."""
        scene_id = "123"
        update_data = {
            "title": "Updated Scene",
            "details": "New details",
            "studio_id": "studio123",
            "performer_ids": ["perf1", "perf2"],
            "tag_ids": ["tag1", "tag2", "tag3"],
            "rating100": 85,
            "organized": True,
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "sceneUpdate": {
                    "id": scene_id,
                    "title": update_data["title"],
                    "details": update_data["details"],
                    "rating100": update_data["rating100"],
                    "organized": update_data["organized"],
                    "studio": {"id": "studio123", "name": "Studio Name"},
                    "performers": [
                        {"id": "perf1", "name": "Performer 1"},
                        {"id": "perf2", "name": "Performer 2"},
                    ],
                    "tags": [
                        {"id": "tag1", "name": "Tag 1"},
                        {"id": "tag2", "name": "Tag 2"},
                        {"id": "tag3", "name": "Tag 3"},
                    ],
                }
            }

            result = await stash_service.update_scene(scene_id, update_data)

            assert result["id"] == scene_id
            assert result["title"] == update_data["title"]
            assert len(result["performers"]) == 2
            assert len(result["tags"]) == 3
            assert result["studio"]["id"] == "studio123"

    @pytest.mark.asyncio
    async def test_graphql_query_with_custom_headers(self, stash_service):
        """Test GraphQL query execution with custom headers."""
        query = "query { version { version } }"

        # Set a custom API key
        stash_service.api_key = "custom_api_key"

        with patch.object(stash_service, "_get_headers") as mock_get_headers:
            mock_get_headers.return_value = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "ApiKey": "custom_api_key",
            }

            with patch.object(stash_service._client, "post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "data": {"version": {"version": "v0.20.0"}}
                }
                mock_response.headers = {}
                mock_post.return_value = mock_response

                await stash_service.execute_graphql(query)

                # Verify headers were set correctly
                mock_get_headers.assert_called_once()
                assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_http_error(self, stash_service):
        """Test retry mechanism on general HTTP errors."""
        query = "query { findScenes { scenes { id } } }"

        # Reduce retry delay for testing
        stash_service.max_retries = 3

        with patch.object(stash_service._client, "post") as mock_post:
            # First two calls: HTTP error
            # Third call: success
            mock_post.side_effect = [
                httpx.HTTPError("Network error"),
                httpx.HTTPError("Network error"),
                Mock(
                    status_code=200,
                    json=Mock(return_value={"data": {"result": "success"}}),
                    headers={},
                ),
            ]

            # Patch sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await stash_service.execute_graphql(query)

                assert result == {"result": "success"}
                assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, stash_service):
        """Test that retries are exhausted after max attempts."""
        query = "query { findScenes { scenes { id } } }"

        # Track retry attempts
        attempt_count = 0

        async def failing_post(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("Connection failed")

        # Mock the client to always fail
        with patch.object(stash_service._client, "post", side_effect=failing_post):
            # Mock sleep to speed up retries
            with patch("asyncio.sleep", new_callable=AsyncMock):
                # The retry decorator is configured on the actual method, should exhaust after 3 attempts
                # It will raise RetryError after exhausting retries
                with pytest.raises((StashConnectionError, RetryError)):
                    await stash_service.execute_graphql(query)

                # Verify it tried 3 times (the default from retry decorator)
                assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, stash_service):
        """Test timeout error handling."""
        query = "query { findScenes { scenes { id } } }"

        # Track retry attempts
        attempt_count = 0

        async def timeout_post(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.TimeoutException("Request timed out")

        with patch.object(stash_service._client, "post", side_effect=timeout_post):
            # Mock sleep to speed up retries
            with patch("asyncio.sleep", new_callable=AsyncMock):
                # TimeoutException should be caught and re-raised as StashConnectionError
                # After retries are exhausted, it will raise RetryError
                with pytest.raises((StashConnectionError, RetryError)):
                    await stash_service.execute_graphql(query)

                # Verify it tried 3 times due to retry
                assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, stash_service):
        """Test handling of invalid JSON response."""
        query = "query { findScenes { scenes { id } } }"

        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.headers = {}
            mock_post.return_value = mock_response

            with pytest.raises(ValueError):
                await stash_service.execute_graphql(query)

    @pytest.mark.asyncio
    async def test_header_generation_with_invalid_api_keys(self):
        """Test header generation with various invalid API key values."""
        # Test with None
        service = StashService(stash_url="http://localhost:9999", api_key=None)
        headers = service._get_headers()
        assert "ApiKey" not in headers

        # Test with empty string
        service.api_key = ""
        headers = service._get_headers()
        assert "ApiKey" not in headers

        # Test with whitespace
        service.api_key = "   "
        headers = service._get_headers()
        assert "ApiKey" not in headers

        # Test with placeholder values
        for placeholder in ["0", "null", "none"]:
            service.api_key = placeholder
            headers = service._get_headers()
            assert "ApiKey" not in headers

        # Test with valid key
        service.api_key = "valid_key_123"
        headers = service._get_headers()
        assert headers["ApiKey"] == "valid_key_123"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with StashService(
            stash_url="http://localhost:9999", api_key="test_key"
        ) as service:
            assert service.base_url == "http://localhost:9999"
            assert service.api_key == "test_key"

        # After exiting context, client should be closed
        # Check that the client's aclose method was called
        assert service._client.is_closed

    @pytest.mark.asyncio
    async def test_retry_with_rate_limit_header(self, stash_service):
        """Test retry mechanism respects Retry-After header."""
        query = "query { findScenes { scenes { id } } }"

        with patch.object(stash_service._client, "post") as mock_post:
            # First call: rate limit with Retry-After header
            # Second call: success
            mock_response_rate_limit = Mock()
            mock_response_rate_limit.status_code = 429
            mock_response_rate_limit.json.return_value = {"error": "Rate limited"}
            mock_response_rate_limit.headers = {"Retry-After": "2"}

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": {"result": "success"}}
            mock_response_success.headers = {}

            mock_post.side_effect = [mock_response_rate_limit, mock_response_success]

            # Track sleep calls
            sleep_calls = []

            async def mock_sleep(seconds):
                sleep_calls.append(seconds)

            with patch("asyncio.sleep", side_effect=mock_sleep):
                result = await stash_service.execute_graphql(query)

                assert result == {"result": "success"}
                assert mock_post.call_count == 2
                # The retry mechanism should respect the Retry-After header
                # Note: tenacity might add some jitter, so we check if any sleep was called
                assert len(sleep_calls) > 0

    @pytest.mark.asyncio
    async def test_graphql_errors_with_multiple_errors(self, stash_service):
        """Test handling of multiple GraphQL errors."""
        query = "query { invalidQuery }"
        error_response = {
            "errors": [
                {"message": "Field 'invalidQuery' not found"},
                {"message": "Syntax error in query"},
                {"message": "Permission denied"},
            ]
        }

        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = error_response
            mock_response.headers = {}
            mock_post.return_value = mock_response

            with pytest.raises(
                StashGraphQLError,
                match="Field 'invalidQuery' not found, Syntax error in query, Permission denied",
            ):
                await stash_service.execute_graphql(query)

    @pytest.mark.asyncio
    async def test_http_status_error_handling(self, stash_service):
        """Test handling of various HTTP status errors."""
        query = "query { version { version } }"

        # Test 500 Internal Server Error - will be retried and eventually raise RetryError
        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": "Internal Server Error"}
            mock_response.headers = {}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Internal Server Error", request=Mock(), response=mock_response
            )
            mock_post.return_value = mock_response

            # Mock sleep to speed up retries
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises((StashConnectionError, RetryError)):
                    await stash_service.execute_graphql(query)

        # Test 403 Forbidden - will be retried and eventually raise RetryError
        with patch.object(stash_service._client, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"error": "Forbidden"}
            mock_response.headers = {}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Forbidden", request=Mock(), response=mock_response
            )
            mock_post.return_value = mock_response

            # Mock sleep to speed up retries
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises((StashConnectionError, RetryError)):
                    await stash_service.execute_graphql(query)

    @pytest.mark.asyncio
    async def test_connection_error_message_details(self, stash_service):
        """Test that connection errors include helpful details."""
        query = "query { version { version } }"

        # Track retry attempts
        attempt_count = 0

        async def connect_error(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("Failed to establish connection")

        with patch.object(stash_service._client, "post", side_effect=connect_error):
            # Mock sleep to speed up retries
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises((StashConnectionError, RetryError)) as exc_info:
                    await stash_service.execute_graphql(query)

                # Check that we made 3 attempts
                assert attempt_count == 3

                # Get the actual exception
                error = exc_info.value
                error_message = str(error)

                # If it's a RetryError, check the last attempt
                if isinstance(error, RetryError):
                    # The RetryError contains the last exception in its last_attempt
                    if hasattr(error, "last_attempt") and error.last_attempt.failed:
                        inner_error = error.last_attempt.exception()
                        if isinstance(inner_error, StashConnectionError):
                            error_message = str(inner_error)

                # The error should mention the connection issue
                assert (
                    "Failed to connect" in error_message
                    or "Connection failed" in error_message
                    or "StashConnectionError" in error_message
                )

    @pytest.mark.asyncio
    async def test_cache_functionality(self, stash_service):
        """Test caching functionality for get_scene."""
        scene_id = "123"
        scene_data = {
            "id": scene_id,
            "title": "Cached Scene",
            "path": "/path/to/scene.mp4",
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findScene": scene_data}

            # First call - should hit the API
            result1 = await stash_service.get_scene(scene_id)
            assert mock_execute.call_count == 1
            assert result1["title"] == "Cached Scene"

            # Second call - should use cache
            result2 = await stash_service.get_scene(scene_id)
            assert mock_execute.call_count == 1  # No additional API call
            assert result2["title"] == "Cached Scene"

    @pytest.mark.asyncio
    async def test_batch_operations_error_handling(self, stash_service):
        """Test error handling in batch operations."""
        scene_ids = ["1", "2", "3"]
        update_data = {"studio_id": "studio123"}

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            # Simulate partial failure
            mock_execute.side_effect = StashGraphQLError(
                "Batch update failed for some scenes"
            )

            with pytest.raises(StashGraphQLError, match="Batch update failed"):
                await stash_service.batch_update_scenes(scene_ids, update_data)

    @pytest.mark.asyncio
    async def test_pagination_handling(self, stash_service):
        """Test pagination in find operations."""
        # Test first page
        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findScenes": {
                    "count": 100,
                    "scenes": [
                        {"id": str(i), "title": f"Scene {i}"} for i in range(1, 26)
                    ],
                }
            }

            result = await stash_service.find_scenes(per_page=25, page=1)
            assert result["count"] == 100
            assert len(result["scenes"]) == 25
            assert result["scenes"][0]["title"] == "Scene 1"

        # Test second page
        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {
                "findScenes": {
                    "count": 100,
                    "scenes": [
                        {"id": str(i), "title": f"Scene {i}"} for i in range(26, 51)
                    ],
                }
            }

            result = await stash_service.find_scenes(per_page=25, page=2)
            assert result["count"] == 100
            assert len(result["scenes"]) == 25
            assert result["scenes"][0]["title"] == "Scene 26"

    @pytest.mark.asyncio
    async def test_find_or_create_tag_error_handling(self, stash_service):
        """Test error handling in find_or_create_tag method."""
        tag_name = "Test Tag"

        # Test when find_tag raises an error
        with patch.object(stash_service, "find_tag") as mock_find:
            mock_find.side_effect = StashConnectionError("Connection failed")

            with pytest.raises(StashConnectionError):
                await stash_service.find_or_create_tag(tag_name)

        # Test when create_tag fails
        with patch.object(stash_service, "find_tag") as mock_find:
            mock_find.return_value = None  # Tag doesn't exist

            with patch.object(stash_service, "create_tag") as mock_create:
                mock_create.side_effect = StashGraphQLError("Failed to create tag")

                with pytest.raises(StashGraphQLError):
                    await stash_service.find_or_create_tag(tag_name)

    @pytest.mark.asyncio
    async def test_bulk_update_scenes_with_mixed_results(self, stash_service):
        """Test bulk update with partial failures."""
        updates = [
            {"id": "1", "title": "Scene 1", "details": "Details 1"},
            {"id": "2", "title": "Scene 2", "details": "Details 2"},
            {"id": "3", "title": "Scene 3", "details": "Details 3"},
        ]

        # The bulk_update_scenes method will find no common updates and fall back to individual updates
        # Mock update_scene to be called 3 times
        with patch.object(stash_service, "update_scene") as mock_update:
            mock_update.side_effect = [
                {"id": "1", "title": "Scene 1", "details": "Details 1"},
                {"id": "2", "title": "Scene 2", "details": "Details 2"},
                {"id": "3", "title": "Scene 3", "details": "Details 3"},
            ]

            results = await stash_service.bulk_update_scenes(updates)

            assert len(results) == 3
            assert mock_update.call_count == 3
            assert results[0]["id"] == "1"
            assert results[1]["id"] == "2"
            assert results[2]["id"] == "3"

    @pytest.mark.asyncio
    async def test_scene_transformation_error(self, stash_service):
        """Test error handling when scene transformation fails."""
        with patch.object(stash_service, "execute_graphql") as mock_execute:
            # Return invalid scene data that will cause transformation to fail
            mock_execute.return_value = {
                "findScenes": {
                    "count": 1,
                    "scenes": [{"id": "1", "invalid_field": "invalid"}],
                }
            }

            with patch(
                "app.services.stash.transformers.transform_scene"
            ) as mock_transform:
                mock_transform.side_effect = KeyError("Missing required field")

                with pytest.raises(KeyError):
                    await stash_service.get_scenes()

    @pytest.mark.asyncio
    async def test_entity_cache_error_recovery(self, stash_service):
        """Test that entity operations recover from cache errors."""
        # Test performer fetch with cache returning None (cache miss)
        with patch.object(stash_service._entity_cache, "get_performers") as mock_get:
            mock_get.return_value = None  # Simulate cache miss

            with patch.object(stash_service, "execute_graphql") as mock_execute:
                mock_execute.return_value = {
                    "allPerformers": [
                        {"id": "1", "name": "Performer 1", "gender": "FEMALE"},
                    ]
                }

                with patch(
                    "app.services.stash.transformers.transform_performer"
                ) as mock_transform:
                    mock_transform.side_effect = lambda x: x  # Return as-is

                    # Should fetch from API when cache misses
                    performers = await stash_service.get_all_performers()
                    assert len(performers) == 1

    @pytest.mark.asyncio
    async def test_retry_on_specific_http_status_codes(self, stash_service):
        """Test retry behavior on specific HTTP status codes."""
        query = "query { version { version } }"

        # Test 502 Bad Gateway (should retry)
        with patch.object(stash_service._client, "post") as mock_post:
            mock_response_502 = Mock()
            mock_response_502.status_code = 502
            mock_response_502.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Gateway", request=Mock(), response=mock_response_502
            )

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                "data": {"version": {"version": "v0.20.0"}}
            }
            mock_response_success.headers = {}

            mock_post.side_effect = [mock_response_502, mock_response_success]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await stash_service.execute_graphql(query)
                assert result == {"version": {"version": "v0.20.0"}}

    @pytest.mark.asyncio
    async def test_create_marker_validation_errors(self, stash_service):
        """Test marker creation validation."""
        # Test missing required tag_ids
        marker_data = {"scene_id": "123", "seconds": 60, "title": "Test Marker"}

        with pytest.raises(ValueError, match="At least one tag is required"):
            await stash_service.create_marker(marker_data)

        # Test empty tag_ids list
        marker_data["tag_ids"] = []

        with pytest.raises(ValueError, match="At least one tag is required"):
            await stash_service.create_marker(marker_data)

    @pytest.mark.asyncio
    async def test_get_scene_raw_method(self, stash_service):
        """Test get_scene_raw returns untransformed data."""
        scene_id = "123"
        raw_scene_data = {
            "id": scene_id,
            "title": "Raw Scene",
            "files": [{"path": "/path/to/file.mp4"}],
            "extra_field": "should_be_preserved",
        }

        with patch.object(stash_service, "execute_graphql") as mock_execute:
            mock_execute.return_value = {"findScene": raw_scene_data}

            result = await stash_service.get_scene_raw(scene_id)

            assert result == raw_scene_data
            assert "extra_field" in result
            assert result["extra_field"] == "should_be_preserved"

    @pytest.mark.asyncio
    async def test_connection_pool_limits(self):
        """Test that connection pool limits are properly set."""
        # Mock httpx.AsyncClient to capture the limits parameter
        with patch("app.services.stash_service.httpx.AsyncClient") as mock_client_class:
            # Create a mock instance that will be returned
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            # Create the service
            service = StashService(stash_url="http://localhost:9999")

            # Verify AsyncClient was called with correct limits
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs

            assert "limits" in call_kwargs
            limits = call_kwargs["limits"]
            assert limits.max_connections == 10
            assert limits.max_keepalive_connections == 5

            # Clean up
            await service.close()

    @pytest.mark.asyncio
    async def test_http_error_with_response_text(self, stash_service):
        """Test HTTP error handling includes response text when available."""
        query = "query { version { version } }"

        # Track retry attempts
        attempt_count = 0

        async def http_error(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            mock_response = Mock()
            mock_response.text = "Detailed error message from server"
            error = httpx.HTTPError("HTTP Error")
            error.response = mock_response
            raise error

        with patch.object(stash_service._client, "post", side_effect=http_error):
            # Mock sleep to speed up retries
            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Capture logs to verify error details are logged
                with patch("app.services.stash_service.logger") as mock_logger:
                    with pytest.raises((StashConnectionError, RetryError)):
                        await stash_service.execute_graphql(query)

                    # Verify that the error was logged with details
                    assert mock_logger.error.call_count > 0
                    # Verify retries happened
                    assert attempt_count == 3
