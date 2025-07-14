# Task 06: Sync Functionality Implementation

## Current State
- Database models exist for all entities
- Stash API service is implemented
- No sync logic between Stash and local database
- No tracking of sync history

## Objective
Implement comprehensive synchronization functionality to import and update scenes, performers, tags, and studios from Stash into the local database.

## Requirements

### Sync Service

1. **app/services/sync_service.py** - Main sync orchestrator:
   ```python
   # SyncService class with:
   - Dependency injection for StashService and database
   - Progress tracking and reporting
   - Error handling and recovery
   - Sync statistics collection
   
   # Main methods:
   async def sync_all(
       self,
       job_id: Optional[str] = None,
       force: bool = False
   ) -> SyncResult:
       """Full sync of all entities"""
   
   async def sync_scenes(
       self,
       since: Optional[datetime] = None,
       job_id: Optional[str] = None
   ) -> SyncResult:
       """Sync scenes with optional incremental mode"""
   
   async def sync_scene_by_id(
       self,
       scene_id: str
   ) -> SyncResult:
       """Sync single scene"""
   
   async def sync_entities(self) -> SyncResult:
       """Sync performers, tags, studios"""
   ```

### Sync Strategies

2. **app/services/sync/strategies.py** - Different sync strategies:
   ```python
   # Base strategy class:
   class SyncStrategy(ABC):
       @abstractmethod
       async def should_sync(self, entity: Dict) -> bool:
       
       @abstractmethod
       async def sync_entity(self, entity: Dict) -> None:
   
   # Implementations:
   class FullSyncStrategy(SyncStrategy):
       """Always sync everything"""
   
   class IncrementalSyncStrategy(SyncStrategy):
       """Only sync if newer than last_synced"""
   
   class SmartSyncStrategy(SyncStrategy):
       """Compare checksums/versions"""
   ```

### Entity Sync Handlers

3. **app/services/sync/scene_sync.py** - Scene synchronization:
   ```python
   class SceneSyncHandler:
       async def sync_scene(
           self,
           stash_scene: Dict,
           db: Session
       ) -> Scene:
           """Sync single scene with all relationships"""
           
       async def sync_scene_batch(
           self,
           stash_scenes: List[Dict],
           db: Session
       ) -> List[Scene]:
           """Efficiently sync multiple scenes"""
           
       def _merge_scene_data(
           self,
           existing: Scene,
           stash_data: Dict
       ) -> Scene:
           """Merge Stash data into existing scene"""
   ```

4. **app/services/sync/entity_sync.py** - Other entities:
   ```python
   class EntitySyncHandler:
       async def sync_performers(
           self,
           stash_performers: List[Dict],
           db: Session
       ) -> List[Performer]:
           """Sync all performers"""
           
       async def sync_tags(
           self,
           stash_tags: List[Dict],
           db: Session
       ) -> List[Tag]:
           """Sync all tags"""
           
       async def sync_studios(
           self,
           stash_studios: List[Dict],
           db: Session
       ) -> List[Studio]:
           """Sync all studios"""
           
       async def find_or_create_entity(
           self,
           model_class: Type,
           stash_id: str,
           name: str,
           db: Session
       ) -> Any:
           """Generic find or create for entities"""
   ```

### Progress Tracking

5. **app/services/sync/progress.py** - Progress reporting:
   ```python
   class SyncProgress:
       def __init__(self, job_id: str, total_items: int):
           self.job_id = job_id
           self.total_items = total_items
           self.processed_items = 0
           self.errors = []
           
       async def update(
           self,
           processed: int,
           error: Optional[str] = None
       ):
           """Update progress and notify via WebSocket"""
           
       async def complete(self, result: SyncResult):
           """Mark sync as complete"""
   ```

### Sync Results

6. **app/services/sync/models.py** - Result models:
   ```python
   @dataclass
   class SyncResult:
       started_at: datetime
       completed_at: datetime
       total_items: int
       processed_items: int
       created_items: int
       updated_items: int
       skipped_items: int
       errors: List[SyncError]
       
   @dataclass
   class SyncError:
       entity_type: str
       entity_id: str
       error_message: str
       timestamp: datetime
   ```

### Conflict Resolution

7. **app/services/sync/conflicts.py** - Handle conflicts:
   ```python
   class ConflictResolver:
       def resolve_scene_conflict(
           self,
           local: Scene,
           remote: Dict,
           strategy: str = "remote_wins"
       ) -> Scene:
           """Resolve conflicts between local and remote"""
           
       def detect_changes(
           self,
           local: Scene,
           remote: Dict
       ) -> Dict[str, Any]:
           """Detect what fields have changed"""
   ```

### Sync Scheduling

8. **app/services/sync/scheduler.py** - Scheduled sync:
   ```python
   class SyncScheduler:
       def __init__(self, scheduler: AsyncIOScheduler):
           self.scheduler = scheduler
           
       def schedule_full_sync(
           self,
           cron_expression: str
       ):
           """Schedule regular full sync"""
           
       def schedule_incremental_sync(
           self,
           interval_minutes: int
       ):
           """Schedule incremental sync"""
   ```

### Database Operations

9. **app/repositories/sync_repository.py** - DB operations:
   ```python
   class SyncRepository:
       def bulk_upsert_scenes(
           self,
           scenes: List[Dict],
           db: Session
       ) -> List[Scene]:
           """Efficiently upsert multiple scenes"""
           
       def get_last_sync_time(
           self,
           entity_type: str,
           db: Session
       ) -> Optional[datetime]:
           """Get last successful sync time"""
           
       def mark_entity_synced(
           self,
           entity: Any,
           db: Session
       ):
           """Update last_synced timestamp"""
   ```

### API Integration

10. **Update app/api/routes/sync.py**:
    ```python
    @router.post("/sync/all")
    async def sync_all(
        background_tasks: BackgroundTasks,
        force: bool = False,
        db: Session = Depends(get_db),
        sync_service: SyncService = Depends(get_sync_service)
    ):
        """Trigger full sync of all entities"""
        
    @router.post("/sync/scenes")
    async def sync_scenes(
        incremental: bool = True,
        db: Session = Depends(get_db)
    ):
        """Sync scenes only"""
        
    @router.post("/sync/scene/{scene_id}")
    async def sync_single_scene(
        scene_id: str,
        db: Session = Depends(get_db)
    ):
        """Sync specific scene"""
        
    @router.get("/sync/status")
    async def get_sync_status(
        db: Session = Depends(get_db)
    ):
        """Get last sync status and statistics"""
    ```

## Expected Outcome

After completing this task:
- Full sync imports all data from Stash
- Incremental sync updates only changed items
- Individual scenes can be resynced
- Progress is tracked and reported
- Conflicts are handled gracefully
- Sync can be scheduled

## Integration Points
- Uses StashService for API calls
- Updates database models
- Integrates with job tracking
- Reports progress via WebSocket
- Called by API routes

## Success Criteria
1. Full sync imports all scenes successfully
2. Relationships are properly maintained
3. Incremental sync is efficient
4. Progress updates in real-time
5. Errors don't stop entire sync
6. Duplicate data is handled
7. Memory usage is reasonable
8. Sync can be resumed if interrupted
9. Statistics are accurate