"""Stash API service with GraphQL support."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .stash import (
    StashAuthenticationError,
    StashCache,
    StashConnectionError,
    StashEntityCache,
    StashGraphQLError,
    StashRateLimitError,
    mutations,
    queries,
    transformers,
)

logger = logging.getLogger(__name__)


class StashService:
    """Service for interacting with Stash GraphQL API."""

    def __init__(
        self,
        stash_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Stash service.

        Args:
            stash_url: Stash server URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = stash_url.rstrip("/")
        self.graphql_url = f"{self.base_url}/graphql"
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize HTTP client with connection pooling
        # Don't set headers here - we'll set them per request
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

        # Initialize cache
        self._cache = StashCache(max_size=5000, default_ttl=300)
        self._entity_cache = StashEntityCache(self._cache)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        # Only add API key if it's a valid value
        # Exclude: None, empty strings, and common placeholder values like '0', 'null', 'none'
        # These can come from database defaults or uninitialized settings
        if (
            self.api_key
            and self.api_key.strip()
            and self.api_key.strip() not in ["0", "null", "none"]
        ):
            headers["ApiKey"] = self.api_key
        return headers

    async def __aenter__(self) -> "StashService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.HTTPError, StashConnectionError, StashRateLimitError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def execute_graphql(
        self, query: str, variables: Optional[Dict] = None
    ) -> Dict:
        """
        Execute raw GraphQL query with retry logic.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            GraphQL response data

        Raises:
            StashConnectionError: Connection failed
            StashAuthenticationError: Authentication failed
            StashGraphQLError: GraphQL query failed
        """
        payload = {"query": query, "variables": variables or {}}

        # Debug logging for troubleshooting
        logger.debug(f"GraphQL Request URL: {self.graphql_url}")
        logger.debug(f"GraphQL Request Query: {query[:200]}...")  # First 200 chars
        logger.debug(f"GraphQL Request Variables: {variables}")

        # Get headers and log them for debugging
        headers = self._get_headers()
        logger.debug(f"GraphQL Request Headers: {headers}")

        try:
            response = await self._client.post(
                self.graphql_url, json=payload, headers=headers
            )

            if response.status_code == 401:
                raise StashAuthenticationError(
                    "Authentication failed. Check your API key."
                )
            elif response.status_code == 429:
                raise StashRateLimitError("Rate limit exceeded")

            response.raise_for_status()

            data = response.json()

            # Debug logging for troubleshooting
            logger.debug(f"GraphQL Response Status: {response.status_code}")
            logger.debug(
                f"GraphQL Response Data: {str(data)[:500]}..."
            )  # First 500 chars

            if "errors" in data:
                error_messages = [
                    e.get("message", "Unknown error") for e in data["errors"]
                ]
                logger.error(f"GraphQL Errors: {data['errors']}")
                raise StashGraphQLError(
                    f"GraphQL errors: {', '.join(error_messages)}",
                    errors=data["errors"],
                )

            return data.get("data", {})  # type: ignore[no-any-return]

        except httpx.ConnectError as e:
            logger.error(f"Connection error to {self.base_url}: {e}")
            raise StashConnectionError(
                f"Failed to connect to Stash at {self.base_url}: {e}"
            )
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise StashConnectionError(f"Request timed out: {e}")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(
                f"Response text: {e.response.text if hasattr(e, 'response') else 'N/A'}"
            )
            raise StashConnectionError(f"HTTP error: {e}")

    # Scene Operations

    async def get_scenes(
        self,
        page: int = 1,
        per_page: int = 100,
        filter: Optional[Dict] = None,
        sort: Optional[str] = None,
    ) -> Tuple[List[Dict], int]:
        """
        Fetch scenes with pagination.

        Args:
            page: Page number (1-based)
            per_page: Number of scenes per page
            filter: Optional filter criteria
            sort: Optional sort field

        Returns:
            Tuple of (scenes list, total count)
        """
        # Build the filter for pagination
        find_filter: Dict[str, Union[int, str]] = {
            "page": page,
            "per_page": per_page,
        }

        if sort:
            find_filter["sort"] = sort
            find_filter["direction"] = "DESC"

        variables = {
            "filter": find_filter,
            "scene_filter": filter or {},
        }

        # Log the filter being used
        if filter:
            logger.info(f"🔍 Executing GraphQL query with scene_filter: {filter}")
        else:
            logger.info(
                "🔍 Executing GraphQL query with NO scene_filter (getting ALL scenes)"
            )
        logger.debug(f"Full variables: {variables}")

        result = await self.execute_graphql(queries.GET_SCENES, variables)
        logger.debug(
            f"get_scenes GraphQL result keys: {list(result.keys()) if result else 'None'}"
        )

        scenes_data = result.get("findScenes", {})
        logger.debug(
            f"findScenes data keys: {list(scenes_data.keys()) if scenes_data else 'None'}"
        )
        raw_scenes = scenes_data.get("scenes", [])
        logger.debug(f"Raw scenes count: {len(raw_scenes)}")

        scenes = []
        for idx, s in enumerate(raw_scenes):
            try:
                transformed = transformers.transform_scene(s)
                scenes.append(transformed)
                if idx == 0:  # Log first scene for debugging
                    logger.debug(
                        f"First scene transformed keys: {list(transformed.keys()) if transformed else 'None'}"
                    )
            except Exception as e:
                logger.error(f"Error transforming scene at index {idx}: {str(e)}")
                logger.debug(f"Transform error: {type(e).__name__}, value: {repr(e)}")
                logger.debug(f"Scene data that failed: {s}")
                raise

        total_count = scenes_data.get("count", 0)
        logger.debug(
            f"get_scenes returning {len(scenes)} scenes, total_count: {total_count}"
        )

        return scenes, total_count

    async def get_scene(self, scene_id: str) -> Optional[Dict]:
        """
        Get single scene by ID.

        Args:
            scene_id: Stash scene ID

        Returns:
            Scene data or None if not found
        """
        # Check cache first
        cache_key = f"scene:{scene_id}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[no-any-return]

        result = await self.execute_graphql(queries.GET_SCENE_BY_ID, {"id": scene_id})

        scene_data = result.get("findScene")
        if not scene_data:
            return None

        scene = transformers.transform_scene(scene_data)
        self._cache.set(cache_key, scene, ttl=600)  # Cache for 10 minutes

        return scene

    async def find_scenes(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        performers: Optional[List[str]] = None,
        studios: Optional[List[str]] = None,
        organized: Optional[bool] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        Search scenes with filters.

        Args:
            query: Text search query
            tags: List of tag IDs to filter by
            performers: List of performer IDs to filter by
            studios: List of studio IDs to filter by
            organized: Filter by organized status
            page: Page number
            per_page: Results per page

        Returns:
            Dictionary with 'count' and 'scenes' keys
        """
        filter_dict = {}

        if query:
            filter_dict["q"] = query
        if tags:
            filter_dict["tags"] = {"value": tags, "modifier": "INCLUDES_ALL"}  # type: ignore[assignment]
        if performers:
            filter_dict["performers"] = {
                "value": performers,
                "modifier": "INCLUDES_ALL",
            }  # type: ignore[assignment]
        if studios:
            filter_dict["studios"] = {"value": studios, "modifier": "INCLUDES_ALL"}  # type: ignore[assignment]
        if organized is not None:
            filter_dict["organized"] = organized  # type: ignore[assignment]

        scenes, total_count = await self.get_scenes(
            page=page, per_page=per_page, filter=filter_dict
        )

        return {"count": total_count, "scenes": scenes}

    async def update_scene(self, scene_id: str, updates: Dict[str, Any]) -> Dict:
        """
        Update scene metadata.

        Args:
            scene_id: Stash scene ID
            updates: Dictionary of fields to update

        Returns:
            Updated scene data
        """
        # Prepare updates for Stash mutation
        stash_updates = transformers.prepare_scene_update(updates)
        stash_updates["id"] = scene_id

        result = await self.execute_graphql(
            mutations.UPDATE_SCENE, {"input": stash_updates}
        )

        # Invalidate cache
        self._cache.delete(f"scene:{scene_id}")

        return transformers.transform_scene(result.get("sceneUpdate", {}))

    async def bulk_update_scenes(self, updates: List[Dict[str, Any]]) -> List[Dict]:
        """
        Update multiple scenes efficiently.

        Args:
            updates: List of update dictionaries, each must have 'id' field

        Returns:
            List of updated scenes
        """
        # Prepare bulk updates
        bulk_input = {"ids": [u["id"] for u in updates if "id" in u], "input": {}}

        # Find common fields to update across all scenes
        common_updates = {}
        if updates:
            first_update = updates[0]
            for key, value in first_update.items():
                if key != "id" and all(u.get(key) == value for u in updates):
                    common_updates[key] = value

        if not common_updates:
            # No common updates, fall back to individual updates
            results = []
            for update in updates:
                if "id" in update:
                    scene_id = update.pop("id")
                    result = await self.update_scene(scene_id, update)
                    results.append(result)
            return results

        # Apply common updates
        bulk_input["input"] = transformers.prepare_scene_update(common_updates)

        result = await self.execute_graphql(
            mutations.BULK_UPDATE_SCENES, {"input": bulk_input}
        )

        # Invalidate cache for updated scenes
        for scene_id in bulk_input["ids"]:
            self._cache.delete(f"scene:{scene_id}")

        return [
            transformers.transform_scene(s) for s in result.get("bulkSceneUpdate", [])
        ]

    async def batch_update_scenes(
        self, scene_ids: List[str], update_data: Dict[str, Any]
    ) -> List[Dict]:
        """
        Batch update scenes - wrapper for bulk_update_scenes for backward compatibility.

        Args:
            scene_ids: List of scene IDs to update
            update_data: Common data to update for all scenes

        Returns:
            List of updated scenes
        """
        updates = [{"id": scene_id, **update_data} for scene_id in scene_ids]
        return await self.bulk_update_scenes(updates)

    # Entity Operations - Performers

    async def get_all_performers(self) -> List[Dict]:
        """Fetch all performers."""
        # Check cache first
        cached = self._entity_cache.get_performers()
        if cached:
            logger.debug(f"Returning {len(cached)} cached performers")
            return cached

        logger.debug("Fetching all performers from Stash")
        result = await self.execute_graphql(queries.GET_ALL_PERFORMERS)
        logger.debug(f"GraphQL result keys: {list(result.keys())}")

        raw_performers = result.get("allPerformers", [])
        logger.debug(f"Raw performers count: {len(raw_performers)}")

        # Log for debugging
        if not raw_performers:
            logger.warning("No performers returned from Stash")
        elif raw_performers:
            logger.debug(f"First raw performer: {raw_performers[0]}")

        performers = [transformers.transform_performer(p) for p in raw_performers]
        logger.debug(f"Transformed performers count: {len(performers)}")

        # Cache the results
        self._entity_cache.set_performers(performers)

        return performers

    async def create_performer(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Create new performer.

        Args:
            name: Performer name
            **kwargs: Additional performer fields

        Returns:
            Created performer data
        """
        input_data = {"name": name, **kwargs}

        result = await self.execute_graphql(
            mutations.CREATE_PERFORMER, {"input": input_data}
        )

        # Invalidate performer cache
        self._entity_cache.invalidate_performers()

        return transformers.transform_performer(result.get("performerCreate", {}))

    async def find_performer(self, name: str) -> Optional[Dict]:
        """Find performer by name."""
        # Check cache first
        cached = self._entity_cache.get_performer_by_name(name)
        if cached:
            return cached

        filter_dict = {"name": {"value": name, "modifier": "EQUALS"}}

        result = await self.execute_graphql(
            queries.FIND_PERFORMER, {"filter": filter_dict}
        )

        performers = result.get("findPerformers", {}).get("performers", [])
        if performers:
            performer = transformers.transform_performer(performers[0])
            # Cache the result
            self._cache.set(
                f"entities:performers:name:{name.lower()}", performer, ttl=3600
            )
            return performer

        return None

    async def find_performers(
        self, filter: Optional[Dict] = None, page: int = 1, per_page: int = 100
    ) -> Dict:
        """
        Search performers with filters.

        Args:
            filter: Filter criteria
            page: Page number
            per_page: Results per page

        Returns:
            Dictionary with 'count' and 'performers' keys
        """
        variables = {"filter": filter or {}, "page": page, "per_page": per_page}

        result = await self.execute_graphql(queries.FIND_PERFORMER, variables)

        performers_data = result.get("findPerformers", {})
        return {
            "count": performers_data.get("count", 0),
            "performers": [
                transformers.transform_performer(p)
                for p in performers_data.get("performers", [])
            ],
        }

    # Entity Operations - Tags

    async def get_all_tags(self) -> List[Dict]:
        """Fetch all tags."""
        # Check cache first
        cached = self._entity_cache.get_tags()
        if cached:
            logger.debug(f"Returning {len(cached)} cached tags")
            return cached

        logger.debug("Fetching all tags from Stash")
        result = await self.execute_graphql(queries.GET_ALL_TAGS)
        logger.debug(f"GraphQL result keys: {list(result.keys())}")

        raw_tags = result.get("allTags", [])
        logger.debug(f"Raw tags count: {len(raw_tags)}")

        # Log for debugging
        if not raw_tags:
            logger.warning("No tags returned from Stash")
        elif raw_tags:
            logger.debug(f"First raw tag: {raw_tags[0]}")

        tags = [transformers.transform_tag(t) for t in raw_tags]
        logger.debug(f"Transformed tags count: {len(tags)}")

        # Cache the results
        self._entity_cache.set_tags(tags)

        return tags

    async def create_tag(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Create new tag.

        Args:
            name: Tag name
            **kwargs: Additional tag fields

        Returns:
            Created tag data
        """
        input_data = {"name": name, **kwargs}

        result = await self.execute_graphql(mutations.CREATE_TAG, {"input": input_data})

        # Invalidate tag cache
        self._entity_cache.invalidate_tags()

        return transformers.transform_tag(result.get("tagCreate", {}))

    async def find_tag(self, name: str) -> Optional[Dict]:
        """Find tag by name."""
        # Check cache first
        cached = self._entity_cache.get_tag_by_name(name)
        if cached:
            return cached

        filter_dict = {"name": {"value": name, "modifier": "EQUALS"}}

        result = await self.execute_graphql(queries.FIND_TAG, {"filter": filter_dict})

        tags = result.get("findTags", {}).get("tags", [])
        if tags:
            tag = transformers.transform_tag(tags[0])
            # Cache the result
            self._cache.set(f"entities:tags:name:{name.lower()}", tag, ttl=3600)
            return tag

        return None

    async def find_or_create_tag(self, name: str) -> Optional[str]:
        """Find or create a tag by name and return its ID.

        Args:
            name: Tag name

        Returns:
            Tag ID if found or created, None otherwise
        """
        # First try to find existing tag
        existing_tag = await self.find_tag(name)
        if existing_tag:
            return existing_tag.get("id")

        # Create new tag if not found
        new_tag = await self.create_tag(name)
        if new_tag:
            return new_tag.get("id")

        return None

    # Entity Operations - Studios

    async def get_all_studios(self) -> List[Dict]:
        """Fetch all studios."""
        # Check cache first
        cached = self._entity_cache.get_studios()
        if cached:
            logger.debug(f"Returning {len(cached)} cached studios")
            return cached

        logger.debug("Fetching all studios from Stash")
        result = await self.execute_graphql(queries.GET_ALL_STUDIOS)
        logger.debug(f"GraphQL result keys: {list(result.keys())}")

        raw_studios = result.get("allStudios", [])
        logger.debug(f"Raw studios count: {len(raw_studios)}")

        # Log for debugging
        if not raw_studios:
            logger.warning("No studios returned from Stash")
        elif raw_studios:
            logger.debug(f"First raw studio: {raw_studios[0]}")

        studios = [transformers.transform_studio(s) for s in raw_studios]
        logger.debug(f"Transformed studios count: {len(studios)}")

        # Cache the results
        self._entity_cache.set_studios(studios)

        return studios

    async def create_studio(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Create new studio.

        Args:
            name: Studio name
            **kwargs: Additional studio fields

        Returns:
            Created studio data
        """
        input_data = {"name": name, **kwargs}

        result = await self.execute_graphql(
            mutations.CREATE_STUDIO, {"input": input_data}
        )

        # Invalidate studio cache
        self._entity_cache.invalidate_studios()

        return transformers.transform_studio(result.get("studioCreate", {}))

    async def find_studio(self, name: str) -> Optional[Dict]:
        """Find studio by name."""
        # Check cache first
        cached = self._entity_cache.get_studio_by_name(name)
        if cached:
            return cached

        filter_dict = {"name": {"value": name, "modifier": "EQUALS"}}

        result = await self.execute_graphql(
            queries.FIND_STUDIO, {"filter": filter_dict}
        )

        studios = result.get("findStudios", {}).get("studios", [])
        if studios:
            studio = transformers.transform_studio(studios[0])
            # Cache the result
            self._cache.set(f"entities:studios:name:{name.lower()}", studio, ttl=3600)
            return studio

        return None

    # Utility Methods

    async def test_connection(self) -> bool:
        """
        Test Stash API connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = await self.execute_graphql(queries.TEST_CONNECTION)
            version_info = result.get("version", {})
            logger.info(f"Connected to Stash v{version_info.get('version', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def get_stats(self) -> Dict:
        """
        Get Stash statistics.

        Returns:
            Dictionary with various statistics
        """
        result = await self.execute_graphql(queries.GET_STATS)
        return result.get("stats", {})  # type: ignore[no-any-return]

    # Incremental sync methods

    async def get_performers_since(self, since: datetime) -> List[Dict]:
        """Get performers created or updated since a specific time."""
        filter_dict = {
            "updated_at": {"value": since.isoformat(), "modifier": "GREATER_THAN"}
        }

        result = await self.execute_graphql(
            queries.FIND_PERFORMERS_BY_UPDATED, {"filter": filter_dict}
        )

        raw_performers = result.get("findPerformers", {}).get("performers", [])
        return [transformers.transform_performer(p) for p in raw_performers]

    async def get_tags_since(self, since: datetime) -> List[Dict]:
        """Get tags created or updated since a specific time."""
        filter_dict = {
            "updated_at": {"value": since.isoformat(), "modifier": "GREATER_THAN"}
        }

        result = await self.execute_graphql(
            queries.FIND_TAGS_BY_UPDATED, {"filter": filter_dict}
        )

        raw_tags = result.get("findTags", {}).get("tags", [])
        return [transformers.transform_tag(t) for t in raw_tags]

    async def get_studios_since(self, since: datetime) -> List[Dict]:
        """Get studios created or updated since a specific time."""
        filter_dict = {
            "updated_at": {"value": since.isoformat(), "modifier": "GREATER_THAN"}
        }

        result = await self.execute_graphql(
            queries.FIND_STUDIOS_BY_UPDATED, {"filter": filter_dict}
        )

        raw_studios = result.get("findStudios", {}).get("studios", [])
        return [transformers.transform_studio(s) for s in raw_studios]

    async def create_marker(self, marker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scene marker.

        Args:
            marker_data: Dictionary containing:
                - scene_id: ID of the scene
                - seconds: Time position in seconds
                - title: Marker title (optional)
                - tag_ids: List of tag IDs (at least one required)

        Returns:
            Created marker data
        """
        # Prepare input for mutation
        input_data = {
            "scene_id": marker_data["scene_id"],
            "seconds": marker_data["seconds"],
            "title": marker_data.get("title", ""),
        }

        # Stash requires at least one tag for markers
        tag_ids = marker_data.get("tag_ids", [])
        if tag_ids:
            # First tag is the primary tag
            input_data["primary_tag_id"] = tag_ids[0]
            # Additional tags if any
            if len(tag_ids) > 1:
                input_data["tag_ids"] = tag_ids[1:]
        else:
            raise ValueError("At least one tag is required for scene markers")

        result = await self.execute_graphql(
            mutations.CREATE_SCENE_MARKER, {"input": input_data}
        )

        marker_result: Dict[str, Any] = result.get("sceneMarkerCreate", {})
        return marker_result


# Maintain backward compatibility with old class name
StashClient = StashService
