# Task 05: Stash API Service Implementation

## Current State
- Database models are defined
- Basic service structure exists
- Stash connection settings configured
- No actual Stash API integration

## Objective
Implement a comprehensive service for interacting with the Stash GraphQL API, including scene fetching, metadata updates, and entity management.

## Requirements

### Base Stash Service

1. **app/services/stash_service.py** - Main service class:
   ```python
   # StashService class with:
   - __init__(stash_url, api_key)
   - Connection pooling with httpx
   - Retry logic for failed requests
   - Error handling and logging
   - Request timeout configuration
   ```

### GraphQL Queries

2. **app/services/stash/queries.py** - GraphQL query definitions:
   ```python
   # Query fragments and full queries:
   
   # Scene fragment with all fields:
   SCENE_FRAGMENT = """
     fragment SceneData on Scene {
       id
       title
       paths
       organized
       details
       created_at
       date
       studio { id name }
       performers { id name }
       tags { id name }
     }
   """
   
   # Queries to implement:
   - GET_SCENES (with pagination and filters)
   - GET_SCENE_BY_ID
   - GET_ALL_PERFORMERS
   - GET_ALL_TAGS  
   - GET_ALL_STUDIOS
   - FIND_SCENES (with complex filters)
   ```

### GraphQL Mutations

3. **app/services/stash/mutations.py** - GraphQL mutations:
   ```python
   # Mutations to implement:
   - UPDATE_SCENE (all fields)
   - CREATE_PERFORMER
   - CREATE_TAG
   - CREATE_STUDIO
   - BULK_UPDATE_SCENES
   ```

### Service Methods

4. **Scene Operations** in StashService:
   ```python
   # Methods to implement:
   
   async def get_scenes(
       self,
       page: int = 1,
       per_page: int = 100,
       filter: Optional[Dict] = None,
       sort: Optional[str] = None
   ) -> Tuple[List[Dict], int]:
       """Fetch scenes with pagination"""
   
   async def get_scene(self, scene_id: str) -> Optional[Dict]:
       """Get single scene by ID"""
   
   async def find_scenes(
       self,
       query: Optional[str] = None,
       tags: Optional[List[str]] = None,
       performers: Optional[List[str]] = None,
       studios: Optional[List[str]] = None,
       organized: Optional[bool] = None
   ) -> List[Dict]:
       """Search scenes with filters"""
   
   async def update_scene(
       self,
       scene_id: str,
       updates: Dict[str, Any]
   ) -> Dict:
       """Update scene metadata"""
   
   async def bulk_update_scenes(
       self,
       updates: List[Dict[str, Any]]
   ) -> List[Dict]:
       """Update multiple scenes efficiently"""
   ```

5. **Entity Operations** in StashService:
   ```python
   # Methods for performers, tags, studios:
   
   async def get_all_performers(self) -> List[Dict]:
       """Fetch all performers"""
   
   async def create_performer(self, name: str) -> Dict:
       """Create new performer"""
   
   async def find_performer(self, name: str) -> Optional[Dict]:
       """Find performer by name"""
   
   async def get_all_tags(self) -> List[Dict]:
       """Fetch all tags"""
   
   async def create_tag(self, name: str) -> Dict:
       """Create new tag"""
   
   async def find_tag(self, name: str) -> Optional[Dict]:
       """Find tag by name"""
   
   async def get_all_studios(self) -> List[Dict]:
       """Fetch all studios"""
   
   async def create_studio(self, name: str) -> Dict:
       """Create new studio"""
   
   async def find_studio(self, name: str) -> Optional[Dict]:
       """Find studio by name"""
   ```

6. **Utility Methods**:
   ```python
   async def test_connection(self) -> bool:
       """Test Stash API connection"""
   
   async def get_stats(self) -> Dict:
       """Get Stash statistics"""
   
   async def execute_graphql(
       self,
       query: str,
       variables: Optional[Dict] = None
   ) -> Dict:
       """Execute raw GraphQL query"""
   ```

### Data Transformation

7. **app/services/stash/transformers.py** - Data transformers:
   ```python
   # Functions to transform Stash data:
   
   def transform_scene(stash_scene: Dict) -> Dict:
       """Convert Stash scene to internal format"""
   
   def transform_performer(stash_performer: Dict) -> Dict:
       """Convert Stash performer to internal format"""
   
   def transform_tag(stash_tag: Dict) -> Dict:
       """Convert Stash tag to internal format"""
   
   def transform_studio(stash_studio: Dict) -> Dict:
       """Convert Stash studio to internal format"""
   
   def prepare_scene_update(updates: Dict) -> Dict:
       """Prepare updates for Stash mutation"""
   ```

### Error Handling

8. **app/services/stash/exceptions.py** - Custom exceptions:
   ```python
   # Stash-specific exceptions:
   - StashConnectionError
   - StashAuthenticationError
   - StashNotFoundError
   - StashValidationError
   - StashRateLimitError
   ```

### Caching Layer

9. **app/services/stash/cache.py** - Simple caching:
   ```python
   # In-memory cache for frequently accessed data:
   - Cache performers/tags/studios
   - TTL-based expiration
   - Manual invalidation
   - Size limits
   ```

### Integration with stashapi Library

10. **Alternative Implementation** using stashapi:
    ```python
    # If using the stashapi library:
    - Wrap stashapi.StashInterface
    - Add our custom methods
    - Handle connection pooling
    - Add retry logic
    ```

## Expected Outcome

After completing this task:
- Complete Stash API integration is implemented
- All CRUD operations work for scenes and entities
- Efficient batch operations are supported
- Proper error handling and retries
- Data transformation between formats
- Connection testing functionality

## Integration Points
- Service used by sync functionality
- Called by API routes
- Integrated with database models
- Used by analysis service

## Success Criteria
1. Service connects to Stash successfully
2. Can fetch all scenes with pagination
3. Can update scene metadata
4. Can create missing entities
5. Batch operations are efficient
6. Errors are handled gracefully
7. Connection test endpoint works
8. Data transformations are correct
9. Rate limiting is respected