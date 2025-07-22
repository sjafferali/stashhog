# Implementation Plan for Enhanced Scenes Page

Based on my analysis, here's the comprehensive plan to implement the requested features:

## Overview

This plan outlines the implementation of enhanced scene browsing features that:
- Sort scenes by active job status (running jobs first)
- Display job indicators with links to job monitor
- Allow filtering by:
  - Scenes with active jobs
  - Scenes with unreviewed analysis plans
  - Scenes pending resync from Stash
- Implement an intelligent default sort order: Active jobs → Recent jobs → Last updated

## 1. Backend Changes

### A. Extend Scene API Response Model

**File**: `/backend/app/api/schemas.py`

Add the following fields to `SceneResponse`:

```python
class SceneResponse(BaseModel):
    # ... existing fields ...
    
    # Job-related fields
    active_jobs: List[JobInfo] = Field(default_factory=list, description="Currently running jobs for this scene")
    recent_jobs: List[JobInfo] = Field(default_factory=list, description="Recently completed jobs (last 24-48 hours)")
    
    # Status indicators
    has_pending_changes: bool = Field(default=False, description="Has unreviewed analysis plan changes")
    needs_resync: bool = Field(default=False, description="Scene has updates in Stash not yet synced")

class JobInfo(BaseModel):
    """Minimal job information for scene display"""
    id: str
    type: JobType
    status: JobStatus
    progress: int
    started_at: Optional[datetime]
```

### B. Create Job-Scene Relationship Query Logic

**File**: `/backend/app/repositories/job_repository.py`

Add methods to efficiently query jobs by scene IDs:

```python
async def get_active_jobs_for_scenes(self, scene_ids: List[str], db: AsyncSession) -> Dict[str, List[Job]]:
    """Get active jobs (running/pending) for multiple scenes"""
    # Query jobs where metadata contains scene_ids
    # Use PostgreSQL JSONB operators for efficient lookup
    
async def get_recent_jobs_for_scenes(self, scene_ids: List[str], hours: int = 24, db: AsyncSession) -> Dict[str, List[Job]]:
    """Get recently completed jobs for multiple scenes"""
```

### C. Add New Scene Filters

**File**: `/backend/app/api/schemas.py`

Extend `SceneFilter`:

```python
class SceneFilter(BaseModel):
    # ... existing filters ...
    
    # New filters
    has_active_jobs: Optional[bool] = Field(None, description="Filter scenes with running/pending jobs")
    has_pending_changes: Optional[bool] = Field(None, description="Filter scenes with unreviewed plan changes")
    needs_resync: Optional[bool] = Field(None, description="Filter scenes that need resync from Stash")
```

**File**: `/backend/app/api/routes/scenes.py`

Update `_build_scene_filter_conditions` to handle new filters:

```python
def _build_scene_filter_conditions(filters: SceneFilter, query: Any) -> tuple[Any, list[Any]]:
    # ... existing code ...
    
    if filters.has_pending_changes is not None:
        query = query.outerjoin(Scene.plan_changes)
        if filters.has_pending_changes:
            conditions.append(
                and_(
                    PlanChange.accepted.is_(False),
                    PlanChange.rejected.is_(False),
                    PlanChange.applied.is_(False)
                )
            )
        else:
            conditions.append(
                or_(
                    ~Scene.plan_changes.any(),
                    ~exists().where(
                        and_(
                            PlanChange.scene_id == Scene.id,
                            PlanChange.accepted.is_(False),
                            PlanChange.rejected.is_(False),
                            PlanChange.applied.is_(False)
                        )
                    )
                )
            )
    
    if filters.needs_resync is not None:
        if filters.needs_resync:
            conditions.append(Scene.stash_updated_at > Scene.last_synced)
        else:
            conditions.append(Scene.stash_updated_at <= Scene.last_synced)
```

### D. Implement Enhanced Sorting

**File**: `/backend/app/api/schemas.py`

Add new sort options:

```python
class SortBy(str, Enum):
    # ... existing options ...
    ACTIVE_JOBS = "active_jobs"
    RECENT_JOBS = "recent_jobs"
    COMBINED = "combined"  # Default: active → recent → last_updated
```

**File**: `/backend/app/api/routes/scenes.py`

Implement complex sorting logic:

```python
async def _apply_enhanced_sorting(
    scenes: List[Scene], 
    sort_by: str,
    job_data: Dict[str, List[Job]],
    db: AsyncSession
) -> List[Scene]:
    """Apply enhanced sorting with job status consideration"""
    if sort_by == "combined":
        # Sort scenes into buckets
        active_job_scenes = []
        recent_job_scenes = []
        other_scenes = []
        
        for scene in scenes:
            if scene.id in job_data['active']:
                active_job_scenes.append(scene)
            elif scene.id in job_data['recent']:
                recent_job_scenes.append(scene)
            else:
                other_scenes.append(scene)
        
        # Sort within each bucket by last_updated desc
        active_job_scenes.sort(key=lambda s: s.stash_updated_at, reverse=True)
        recent_job_scenes.sort(key=lambda s: s.stash_updated_at, reverse=True)
        other_scenes.sort(key=lambda s: s.stash_updated_at, reverse=True)
        
        return active_job_scenes + recent_job_scenes + other_scenes
```

### E. Database Optimizations

Add indexes for efficient queries:

```sql
-- Index for JSONB scene_ids lookup in job metadata
CREATE INDEX idx_job_metadata_scene_ids ON job USING gin ((metadata->'scene_ids'));

-- Composite index for resync detection
CREATE INDEX idx_scene_sync_status ON scene (last_synced, stash_updated_at);

-- Index for pending plan changes
CREATE INDEX idx_plan_change_pending ON plan_change (scene_id) 
WHERE accepted = false AND rejected = false AND applied = false;
```

## 2. Frontend Changes

### A. Update Scene Data Types

**File**: `/frontend/src/types/models.ts`

```typescript
export interface Scene {
  // ... existing fields ...
  
  // New fields
  activeJobs: JobInfo[];
  recentJobs: JobInfo[];
  hasPendingChanges: boolean;
  needsResync: boolean;
}

export interface JobInfo {
  id: string;
  type: JobType;
  status: JobStatus;
  progress: number;
  startedAt?: string;
}

export enum SceneSortBy {
  // ... existing options ...
  ACTIVE_JOBS = 'active_jobs',
  RECENT_JOBS = 'recent_jobs',
  COMBINED = 'combined'
}
```

### B. Enhance Scene Cards

**File**: `/frontend/src/pages/scenes/components/GridView.tsx`

Add job status indicators:

```tsx
const SceneCard: React.FC<{ scene: Scene }> = ({ scene }) => {
  const hasActiveJob = scene.activeJobs.length > 0;
  const activeJob = scene.activeJobs[0]; // Show first active job
  
  return (
    <div className="scene-card">
      {/* Existing content */}
      
      {/* Job Status Indicator */}
      {hasActiveJob && (
        <div className="absolute top-2 right-2 flex items-center gap-2">
          <Link 
            href={`/jobs?highlight=${activeJob.id}`}
            className="flex items-center gap-1 bg-blue-500 text-white px-2 py-1 rounded text-sm"
          >
            <Spinner className="w-3 h-3" />
            {activeJob.type === 'sync_scenes' ? 'Syncing' : 'Analyzing'}
            {activeJob.progress > 0 && ` ${activeJob.progress}%`}
          </Link>
        </div>
      )}
      
      {/* Status Badges */}
      <div className="flex gap-2 mt-2">
        {scene.needsResync && (
          <Badge variant="warning" size="sm">
            Needs Resync
          </Badge>
        )}
        {scene.hasPendingChanges && (
          <Badge variant="info" size="sm">
            Unreviewed Plans
          </Badge>
        )}
      </div>
    </div>
  );
};
```

### C. Update Search Bar & Filters

**File**: `/frontend/src/pages/scenes/components/AdvancedFilters.tsx`

Add new filter section:

```tsx
const JobStatusFilters: React.FC = () => {
  const { filters, updateFilter } = useSceneFilters();
  
  return (
    <FilterSection title="Job Status">
      <Checkbox
        checked={filters.has_active_jobs || false}
        onChange={(checked) => updateFilter('has_active_jobs', checked)}
        label="Has Active Jobs"
      />
      <Checkbox
        checked={filters.has_pending_changes || false}
        onChange={(checked) => updateFilter('has_pending_changes', checked)}
        label="Has Unreviewed Plans"
      />
      <Checkbox
        checked={filters.needs_resync || false}
        onChange={(checked) => updateFilter('needs_resync', checked)}
        label="Needs Resync"
      />
    </FilterSection>
  );
};
```

### D. Implement Sorting UI

**File**: `/frontend/src/pages/scenes/components/SortDropdown.tsx`

```tsx
const SortDropdown: React.FC = () => {
  const { pagination, updatePagination } = useSceneFilters();
  
  const sortOptions = [
    { value: 'combined', label: 'Smart Sort (Jobs → Recent → Updated)' },
    { value: 'active_jobs', label: 'Active Jobs First' },
    { value: 'recent_jobs', label: 'Recent Jobs First' },
    { value: 'stash_updated_at', label: 'Last Updated' },
    // ... other options
  ];
  
  return (
    <Select
      value={pagination.sort_by || 'combined'}
      onChange={(value) => updatePagination({ sort_by: value })}
      options={sortOptions}
    />
  );
};
```

### E. Real-time Updates Hook

**File**: `/frontend/src/hooks/useSceneJobs.ts`

```typescript
export const useSceneJobs = (sceneIds: string[]) => {
  const [jobUpdates, setJobUpdates] = useState<Record<string, JobInfo[]>>({});
  
  useEffect(() => {
    // Subscribe to WebSocket updates for these scene IDs
    const unsubscribe = subscribeToJobUpdates(sceneIds, (update) => {
      setJobUpdates(prev => ({
        ...prev,
        [update.sceneId]: update.jobs
      }));
    });
    
    return unsubscribe;
  }, [sceneIds]);
  
  return jobUpdates;
};
```

## 3. Real-time Updates

### A. WebSocket Integration

Extend the existing WebSocket manager to handle scene-specific job updates:

```python
# Backend: /backend/app/services/websocket_manager.py
async def notify_scene_job_update(self, scene_id: str, job: Job):
    """Notify clients about job updates for a specific scene"""
    await self.send_to_topic(
        f"scene:{scene_id}:jobs",
        {
            "type": "job_update",
            "scene_id": scene_id,
            "job": job.to_dict()
        }
    )
```

## 4. Performance Considerations

### A. Query Optimization
- Use database views for complex joins
- Implement query result caching for job-scene relationships
- Batch load job data for visible scenes only

### B. Frontend Optimization
- Virtualize scene grid for large datasets
- Debounce filter changes
- Cache job status data with appropriate TTL

### C. Caching Strategy
```python
# Use Redis for caching job-scene relationships
@cache(ttl=30)  # 30 second cache
async def get_scene_job_data(scene_ids: List[str]) -> Dict[str, List[Job]]:
    # Implementation
```

## 5. Testing Requirements

### A. Backend Tests
- Test new filter conditions with various combinations
- Test sorting logic with edge cases
- Test performance with large datasets
- Test WebSocket notifications

### B. Frontend Tests
- Test filter UI interactions
- Test sort dropdown functionality
- Test job status indicators
- Test real-time updates

## 6. Migration Requirements

### A. Database Migrations
```sql
-- Add indexes for performance
CREATE INDEX idx_job_metadata_scene_ids ON job USING gin ((metadata->'scene_ids'));
CREATE INDEX idx_scene_sync_status ON scene (last_synced, stash_updated_at);
CREATE INDEX idx_plan_change_pending ON plan_change (scene_id) 
WHERE accepted = false AND rejected = false AND applied = false;
```

## 7. Documentation Updates

- Update API documentation for new filters and sort options
- Document WebSocket events for scene job updates
- Add user guide for new filtering and sorting features

## Implementation Priority

1. **Phase 1 - Core Backend** (High Priority)
   - Scene API response enhancements
   - Job-scene relationship queries
   - Basic filtering implementation

2. **Phase 2 - Frontend Display** (High Priority)
   - Job status indicators on scene cards
   - Basic filter UI
   - Sort dropdown implementation

3. **Phase 3 - Advanced Features** (Medium Priority)
   - Real-time WebSocket updates
   - Performance optimizations
   - Caching implementation

4. **Phase 4 - Polish** (Low Priority)
   - Enhanced UI animations
   - Advanced filtering combinations
   - Comprehensive testing

This phased approach allows for incremental delivery while maintaining system stability.