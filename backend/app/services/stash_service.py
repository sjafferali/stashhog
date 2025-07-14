"""Stash API service with GraphQL support."""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from .stash import (
    StashConnectionError,
    StashAuthenticationError,
    StashGraphQLError,
    StashRateLimitError,
    StashCache,
    StashEntityCache
)
from .stash import queries, mutations
from .stash import transformers

logger = logging.getLogger(__name__)


class StashService:
    """Service for interacting with Stash GraphQL API."""
    
    def __init__(self, stash_url: str, api_key: Optional[str] = None,
                 timeout: int = 30, max_retries: int = 3):
        """
        Initialize Stash service.
        
        Args:
            stash_url: Stash server URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = stash_url.rstrip('/')
        self.graphql_url = f"{self.base_url}/graphql"
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize HTTP client with connection pooling
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers=self._get_headers()
        )
        
        # Initialize cache
        self._cache = StashCache(max_size=5000, default_ttl=300)
        self._entity_cache = StashEntityCache(self._cache)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["ApiKey"] = self.api_key
        return headers
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, StashConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def execute_graphql(self, query: str, variables: Optional[Dict] = None) -> Dict:
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
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = await self._client.post(self.graphql_url, json=payload)
            
            if response.status_code == 401:
                raise StashAuthenticationError("Authentication failed. Check your API key.")
            elif response.status_code == 429:
                raise StashRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                error_messages = [e.get("message", "Unknown error") for e in data["errors"]]
                raise StashGraphQLError(
                    f"GraphQL errors: {', '.join(error_messages)}", 
                    errors=data["errors"]
                )
            
            return data.get("data", {})
            
        except httpx.ConnectError as e:
            raise StashConnectionError(f"Failed to connect to Stash at {self.base_url}: {e}")
        except httpx.TimeoutException as e:
            raise StashConnectionError(f"Request timed out: {e}")
        except httpx.HTTPError as e:
            raise StashConnectionError(f"HTTP error: {e}")
    
    # Scene Operations
    
    async def get_scenes(self, page: int = 1, per_page: int = 100,
                        filter: Optional[Dict] = None, sort: Optional[str] = None) -> Tuple[List[Dict], int]:
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
        variables = {
            "page": page,
            "per_page": per_page,
            "filter": filter or {},
            "sort": sort,
            "direction": "DESC" if sort else None
        }
        
        result = await self.execute_graphql(queries.GET_SCENES, variables)
        
        scenes_data = result.get("findScenes", {})
        scenes = [transformers.transform_scene(s) for s in scenes_data.get("scenes", [])]
        total_count = scenes_data.get("count", 0)
        
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
            return cached
        
        result = await self.execute_graphql(
            queries.GET_SCENE_BY_ID,
            {"id": scene_id}
        )
        
        scene_data = result.get("findScene")
        if not scene_data:
            return None
        
        scene = transformers.transform_scene(scene_data)
        self._cache.set(cache_key, scene, ttl=600)  # Cache for 10 minutes
        
        return scene
    
    async def find_scenes(self, query: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         performers: Optional[List[str]] = None,
                         studios: Optional[List[str]] = None,
                         organized: Optional[bool] = None,
                         page: int = 1, per_page: int = 100) -> List[Dict]:
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
            List of matching scenes
        """
        filter_dict = {}
        
        if query:
            filter_dict["q"] = query
        if tags:
            filter_dict["tags"] = {"value": tags, "modifier": "INCLUDES_ALL"}
        if performers:
            filter_dict["performers"] = {"value": performers, "modifier": "INCLUDES_ALL"}
        if studios:
            filter_dict["studios"] = {"value": studios, "modifier": "INCLUDES_ALL"}
        if organized is not None:
            filter_dict["organized"] = organized
        
        scenes, _ = await self.get_scenes(
            page=page,
            per_page=per_page,
            filter=filter_dict
        )
        
        return scenes
    
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
            mutations.UPDATE_SCENE,
            {"input": stash_updates}
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
        bulk_input = {
            "ids": [u["id"] for u in updates if "id" in u],
            "input": {}
        }
        
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
            mutations.BULK_UPDATE_SCENES,
            {"input": bulk_input}
        )
        
        # Invalidate cache for updated scenes
        for scene_id in bulk_input["ids"]:
            self._cache.delete(f"scene:{scene_id}")
        
        return [transformers.transform_scene(s) for s in result.get("bulkSceneUpdate", [])]
    
    # Entity Operations - Performers
    
    async def get_all_performers(self) -> List[Dict]:
        """Fetch all performers."""
        # Check cache first
        cached = self._entity_cache.get_performers()
        if cached:
            return cached
        
        result = await self.execute_graphql(queries.GET_ALL_PERFORMERS)
        performers = [transformers.transform_performer(p) for p in result.get("allPerformers", [])]
        
        # Cache the results
        self._entity_cache.set_performers(performers)
        
        return performers
    
    async def create_performer(self, name: str, **kwargs) -> Dict:
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
            mutations.CREATE_PERFORMER,
            {"input": input_data}
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
            queries.FIND_PERFORMER,
            {"filter": filter_dict}
        )
        
        performers = result.get("findPerformers", {}).get("performers", [])
        if performers:
            performer = transformers.transform_performer(performers[0])
            # Cache the result
            self._cache.set(f"entities:performers:name:{name.lower()}", performer, ttl=3600)
            return performer
        
        return None
    
    # Entity Operations - Tags
    
    async def get_all_tags(self) -> List[Dict]:
        """Fetch all tags."""
        # Check cache first
        cached = self._entity_cache.get_tags()
        if cached:
            return cached
        
        result = await self.execute_graphql(queries.GET_ALL_TAGS)
        tags = [transformers.transform_tag(t) for t in result.get("allTags", [])]
        
        # Cache the results
        self._entity_cache.set_tags(tags)
        
        return tags
    
    async def create_tag(self, name: str, **kwargs) -> Dict:
        """
        Create new tag.
        
        Args:
            name: Tag name
            **kwargs: Additional tag fields
            
        Returns:
            Created tag data
        """
        input_data = {"name": name, **kwargs}
        
        result = await self.execute_graphql(
            mutations.CREATE_TAG,
            {"input": input_data}
        )
        
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
        
        result = await self.execute_graphql(
            queries.FIND_TAG,
            {"filter": filter_dict}
        )
        
        tags = result.get("findTags", {}).get("tags", [])
        if tags:
            tag = transformers.transform_tag(tags[0])
            # Cache the result
            self._cache.set(f"entities:tags:name:{name.lower()}", tag, ttl=3600)
            return tag
        
        return None
    
    # Entity Operations - Studios
    
    async def get_all_studios(self) -> List[Dict]:
        """Fetch all studios."""
        # Check cache first
        cached = self._entity_cache.get_studios()
        if cached:
            return cached
        
        result = await self.execute_graphql(queries.GET_ALL_STUDIOS)
        studios = [transformers.transform_studio(s) for s in result.get("allStudios", [])]
        
        # Cache the results
        self._entity_cache.set_studios(studios)
        
        return studios
    
    async def create_studio(self, name: str, **kwargs) -> Dict:
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
            mutations.CREATE_STUDIO,
            {"input": input_data}
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
            queries.FIND_STUDIO,
            {"filter": filter_dict}
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
        return result.get("stats", {})


# Maintain backward compatibility with old class name
StashClient = StashService