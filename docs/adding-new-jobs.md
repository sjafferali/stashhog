# Adding New Jobs to StashHog

This guide provides a comprehensive checklist and guidelines for engineers adding new job types to the StashHog system. It covers both backend and frontend changes required, with special attention to avoiding common pitfalls like greenlet errors.

## Table of Contents

1. [Backend Changes](#backend-changes)
2. [Frontend Changes](#frontend-changes)
3. [Avoiding Greenlet Errors](#avoiding-greenlet-errors)
4. [Testing Checklist](#testing-checklist)
5. [Example Implementation](#example-implementation)

## Backend Changes

### 1. Add Job Type to Enum

**File**: `backend/app/models/job.py`

Add your new job type to the `JobType` enum:

```python
class JobType(str, enum.Enum):
    # ... existing types ...
    YOUR_NEW_JOB = "your_new_job"
```

Also add it to the PostgreSQL enum list in the Job model:

```python
type: Column = Column(
    PostgreSQLEnum(
        # ... existing types ...
        "YOUR_NEW_JOB",
        name="jobtype",
        create_type=False,
    ),
    nullable=False,
    index=True,
)
```

### 2. Create Job Implementation

**File**: `backend/app/jobs/your_new_job.py`

Create a new file for your job implementation following this template:

```python
"""Your job description."""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


async def your_new_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute your job.
    
    IMPORTANT: Follow these guidelines to avoid greenlet errors:
    1. Create a new database session for each operation
    2. Never pass sessions between functions
    3. Complete all operations before session closes
    4. Use the progress_callback for status updates
    
    Args:
        job_id: Unique job identifier
        progress_callback: Async callback for progress updates (provided by job service)
        cancellation_token: Token to check for job cancellation
        **kwargs: Job parameters from metadata
    """
    logger.info(f"Starting your job {job_id}")
    
    try:
        # Initial progress - use the provided callback
        await progress_callback(0, "Starting your job")
        
        # Initialize services if needed (following sync_jobs pattern)
        settings = await load_settings_with_db_overrides()
        # Initialize any external services here
        # service = YourService(settings.your_service.url, settings.your_service.api_key)
        
        # Create your own session for database operations
        async with AsyncSessionLocal() as db:
            # Check for cancellation
            if cancellation_token and cancellation_token.is_cancelled:
                logger.info(f"Job {job_id} cancelled")
                return {"status": "cancelled", "job_id": job_id}
            
            # Do your work here
            await progress_callback(10, "Processing...")
            
            # Example of proper progress reporting
            total_items = 100
            for i in range(total_items):
                if cancellation_token and cancellation_token.is_cancelled:
                    return {"status": "cancelled", "job_id": job_id}
                
                # Process item
                # ...
                
                # Update progress
                progress = int((i + 1) / total_items * 100)
                await progress_callback(
                    progress, 
                    f"Processing item {i + 1}/{total_items}"
                )
            
            # Commit any database changes
            await db.commit()
        
        # Final progress
        await progress_callback(100, "Job completed")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "processed_items": total_items,
            # Include any other relevant results
        }
        
    except Exception as e:
        error_msg = f"Your job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Don't call progress_callback in error handler - let job service handle it
        raise
    finally:
        # Clean up any external service connections
        # if 'service' in locals():
        #     await service.close()
        pass


def register_your_new_jobs(job_service: JobService) -> None:
    """Register job handlers with the job service."""
    job_service.register_handler(JobType.YOUR_NEW_JOB, your_new_job)
    logger.info("Registered your new job handlers")
```

### 3. Register Job Handler

**File**: `backend/app/jobs/__init__.py`

Import and register your job:

```python
from app.jobs.your_new_job import register_your_new_jobs

def register_all_jobs(job_service: JobService) -> None:
    # ... existing registrations ...
    register_your_new_jobs(job_service)
```

### 4. Update API Schema

**File**: `backend/app/api/schemas/__init__.py`

Add your job type to the `JobType` enum:

```python
class JobType(str, Enum):
    # ... existing types ...
    YOUR_NEW_JOB = "your_new_job"
```

### 5. Add Job Type Mapping (if needed)

**File**: `backend/app/api/routes/jobs.py`

If your job type needs special mapping, add it to `map_job_type_to_schema`:

```python
def map_job_type_to_schema(model_type: str) -> str:
    mapping = {
        # ... existing mappings ...
        "your_new_job": "your_new_job",
    }
    return mapping.get(model_type, model_type)
```

### 6. Create API Endpoint (Optional)

If you need a dedicated endpoint for your job:

```python
@router.post("/your-job")
async def trigger_your_job(
    param1: str = Body(..., description="Parameter 1"),
    param2: bool = Body(False, description="Parameter 2"),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger your job."""
    # Check if already running
    query = select(Job).where(
        Job.type == "your_new_job", 
        Job.status.in_(["pending", "running"])
    )
    result = await db.execute(query)
    existing_job = result.scalar_one_or_none()
    
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job already {existing_job.status}: {existing_job.id}",
        )
    
    # Create job
    from app.models.job import JobType as ModelJobType
    
    job_metadata = {
        "triggered_by": "manual",
        "source": "api",
        "param1": param1,
        "param2": param2,
    }
    
    new_job = await job_service.create_job(
        job_type=ModelJobType.YOUR_NEW_JOB,
        metadata=job_metadata,
        db=db,
    )
    
    # IMPORTANT: Refresh to avoid greenlet errors
    await db.refresh(new_job)
    
    return {
        "success": True,
        "message": "Your job started successfully",
        "job_id": str(new_job.id),
    }
```

**Note**: Job parameters are passed via the `metadata` dictionary. The job service will merge these with kwargs when calling your handler.

## Frontend Changes

### 1. Update Job Type Definition

**File**: `frontend/src/utils/jobUtils.ts`

Add your job type:

```typescript
export type JobType =
  // ... existing types ...
  | 'your_new_job';

export const JOB_TYPE_LABELS: Record<string, string> = {
  // ... existing labels ...
  your_new_job: 'Your Job Display Name',
};

export const JOB_TYPE_COLORS: Record<string, string> = {
  // ... existing colors ...
  your_new_job: 'blue', // Choose: blue, green, purple, orange, cyan, magenta, volcano, geekblue
};

export const JOB_TYPE_DESCRIPTIONS: Record<string, string> = {
  // ... existing descriptions ...
  your_new_job: 'Description of what your job does',
};
```

Update the `formatJobProgress` function if your job has special progress formatting:

```typescript
} else if (type === 'your_new_job') {
  unit = ' items'; // or whatever unit makes sense
}
```

### 2. Update Job Model Interface

**File**: `frontend/src/types/models.ts`

Add your job type to the Job interface:

```typescript
export interface Job {
  // ... existing fields ...
  type:
    // ... existing types ...
    | 'your_new_job';
  // ... rest of interface ...
}
```

### 3. Add to Job Creation Form (if applicable)

**File**: `frontend/src/pages/Scheduler/components/RunJobForm.tsx`

Add your job definition:

```typescript
const jobDefinitions: JobDefinition[] = [
  // ... existing definitions ...
  {
    type: 'your_new_job',
    name: 'Your Job Name',
    description: 'Detailed description of what your job does',
    icon: <YourIcon />, // Import appropriate icon from @ant-design/icons
    category: 'Category', // e.g., 'Synchronization', 'AI Analysis', 'Maintenance'
    parameters: [
      {
        name: 'param1',
        type: 'string',
        required: true,
        description: 'Description of parameter 1',
        placeholder: 'Enter value',
      },
      {
        name: 'param2',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Description of parameter 2',
      },
      // Add more parameters as needed
    ],
  },
];
```

## Important Implementation Details

### Progress Callback

The `progress_callback` parameter is crucial for job status updates:

1. **Type Signature**: `Callable[[int, Optional[str]], Awaitable[None]]`
   - First parameter: Progress percentage (0-100)
   - Second parameter: Optional status message
   - Returns: Awaitable (it's an async function)

2. **Provided by Job Service**: The callback is created and managed by the job service
   - It handles its own database session
   - It automatically updates the job record
   - It sends WebSocket notifications

3. **Usage Guidelines**:
   ```python
   # ✅ CORRECT: Use the provided callback
   await progress_callback(25, "Processing batch 1/4")
   
   # ❌ WRONG: Don't create your own job updates
   job.progress = 25  # Never manually update job fields
   ```

4. **Message Format for Item Counts**:
   - Include "X/Y" pattern for automatic parsing: `"Processed 5/10 items"`
   - The job service will extract item counts from messages matching patterns like:
     - "Processed X/Y"
     - "Synced X/Y"
     - "Applied X/Y"
   - The parsing happens in `backend/app/services/job_service.py:_update_job_progress()`
   - Uses regex: `r"(?:Processed|Synced|Applied) (\d+)/(\d+)"`

### Service Initialization Pattern

Always initialize services using settings:

```python
# Load settings with database overrides
settings = await load_settings_with_db_overrides()

# Initialize external services
stash_service = StashService(
    stash_url=settings.stash.url,
    api_key=settings.stash.api_key
)
```

### Error Handling

```python
except Exception as e:
    logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
    # Don't call progress_callback here - job service handles final status
    raise
```

### Cancellation Support

Check the cancellation token regularly:

```python
if cancellation_token and cancellation_token.is_cancelled:
    logger.info(f"Job {job_id} cancelled")
    return {"status": "cancelled", "job_id": job_id}
```

### Result Dictionary

The job should return a dictionary with standard fields:

```python
return {
    "job_id": job_id,
    "status": "completed",  # or "failed", "cancelled", "completed_with_errors"
    "total_items": total,
    "processed_items": processed,
    "errors": [],  # List of error dictionaries if any
    # Add job-specific fields as needed
}
```

The job service uses the `status` field to determine final job status:
- `"failed"` → JobStatus.FAILED
- `"completed_with_errors"` → JobStatus.COMPLETED (with error count in message)
- `"cancelled"` → JobStatus.CANCELLED
- Default → JobStatus.COMPLETED

### Progress Display in UI

The frontend displays job progress in two ways:

1. **Percentage only**: When no item counts are available
   ```
   75%
   ```

2. **Item counts with units**: When `processed_items` and `total` are available
   ```
   5 / 10 scenes
   3 / 7 performers
   15 / 20 files
   ```

#### Backend: Reporting Item Counts

To have your job display "X / Y items" in the UI:

1. **Option A: Use standard progress message patterns**
   ```python
   await progress_callback(50, "Processed 5/10 records")
   await progress_callback(60, "Synced 6/10 records")
   await progress_callback(70, "Applied 7/10 records")
   ```
   
   The job service automatically extracts counts from these patterns.

2. **Option B: Add custom pattern to job service**
   
   If your job uses different wording, update the regex in `backend/app/services/job_service.py`:
   ```python
   # Current regex (line ~355)
   match = re.search(r"(?:Processed|Synced|Applied) (\d+)/(\d+)", message)
   
   # Add your pattern, e.g., for "Completed X/Y":
   match = re.search(r"(?:Processed|Synced|Applied|Completed) (\d+)/(\d+)", message)
   ```

3. **Option C: Return counts in result**
   ```python
   return {
       "processed_items": 10,
       "total_items": 10,
       # ... other fields
   }
   ```

#### Frontend: Display Units

Add appropriate units for your job type in `frontend/src/utils/jobUtils.ts`:

```typescript
export const formatJobProgress = (
  type: string,
  processed: number | undefined,
  total: number | undefined,
  progress: number
): string => {
  if (total !== undefined && processed !== undefined) {
    let unit = '';
    if (type === 'your_new_job') {
      unit = ' items';  // Change to appropriate unit
    }
    // ... other job types ...
    
    return `${processed} / ${total}${unit}`;
  }
  return `${Math.round(progress)}%`;
};
```

Common units used:
- `scenes` - for scene-related jobs
- `performers`, `tags`, `studios` - for entity sync jobs
- `changes` - for applying modifications
- `files` - for file scanning jobs
- `items` - generic fallback

## Avoiding Greenlet Errors

Based on the greenlet error documentation, follow these critical guidelines to avoid async context issues:

### 1. Database Session Management

**ALWAYS create a new session for each database operation:**

```python
# ✅ CORRECT: Each operation has its own session
async def your_job_handler(job_id: str, progress_callback: Callable, **kwargs):
    # Main work session
    async with AsyncSessionLocal() as db:
        result = await perform_work(db)
        await db.commit()
    
    # Progress updates use the provided callback (it handles its own session)
    await progress_callback(50, "Halfway done")

# ❌ WRONG: Reusing sessions or passing them around
db = some_external_session  # NEVER DO THIS
```

### 2. Progress Callback Usage

**The progress_callback provided by the job service already handles its own session:**

```python
# ✅ CORRECT: Use the provided callback
await progress_callback(25, "Processing batch 1/4")

# ❌ WRONG: Creating your own progress update
async with AsyncSessionLocal() as db:
    job = await db.get(Job, job_id)
    job.progress = 25  # Don't manually update job progress
```

### 3. Handling Lazy Loading

**Load all needed data while the session is active:**

```python
# ✅ CORRECT: Force load relationships before session closes
async with AsyncSessionLocal() as db:
    scenes = await db.execute(select(Scene).options(selectinload(Scene.performers)))
    scenes_list = scenes.scalars().all()
    
    # Access relationships while session is active
    for scene in scenes_list:
        performer_count = len(scene.performers)  # Safe
    
    await db.commit()

# ❌ WRONG: Accessing relationships after session closes
async with AsyncSessionLocal() as db:
    scene = await db.get(Scene, scene_id)
    await db.commit()

# This will fail with greenlet error:
performer_count = len(scene.performers)
```

### 4. Error Handling

**Use a new session for error handling:**

```python
try:
    async with AsyncSessionLocal() as db:
        # Do work
        await db.commit()
except Exception as e:
    # ✅ CORRECT: New session for error handling
    async with AsyncSessionLocal() as error_db:
        await log_error(error_db, job_id, str(e))
        await error_db.commit()
    
    # Let the job service handle the final error status
    raise
```

### 5. Refreshing Objects from Other Services

**When using objects returned from other services:**

```python
# In your API endpoint
job = await job_service.create_job(...)

# ✅ CORRECT: Refresh the job in your current session
await db.refresh(job)
job_id = job.id  # Now safe to access

# ❌ WRONG: Direct access may trigger lazy loading
job = await job_service.create_job(...)
job_id = job.id  # May fail with greenlet error
```

### Complete Progress Reporting Example

Here's a complete example showing how to implement progress reporting that displays "X / Y items":

```python
async def your_new_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Job that processes items with proper progress reporting."""
    
    # Get total items to process
    items = await get_items_to_process()
    total_items = len(items)
    processed_items = 0
    
    await progress_callback(0, f"Starting to process {total_items} items")
    
    for idx, item in enumerate(items):
        if cancellation_token and cancellation_token.is_cancelled:
            return {
                "status": "cancelled",
                "job_id": job_id,
                "total_items": total_items,
                "processed_items": processed_items,
            }
        
        # Process the item
        await process_item(item)
        
        # Update counts and progress
        processed_items = idx + 1
        progress = int((processed_items / total_items) * 100)
        
        # Use standard pattern for automatic parsing
        await progress_callback(
            progress,
            f"Processed {processed_items}/{total_items} items"
        )
    
    return {
        "job_id": job_id,
        "status": "completed",
        "total_items": total_items,
        "processed_items": processed_items,
    }
```

This will display in the UI as:
- During execution: `15 / 30 items` (if you added 'items' unit in frontend)
- Or just: `50%` (if no unit mapping exists)

## Testing Checklist

### Backend Tests

- [ ] Job handler executes successfully
- [ ] Progress updates are reported correctly
- [ ] Cancellation works properly
- [ ] Error handling doesn't cause greenlet errors
- [ ] Job completes with expected result structure
- [ ] Database operations are properly isolated
- [ ] No lazy loading issues after sessions close

### Frontend Tests

- [ ] Job appears in job list with correct label and color
- [ ] Progress displays correctly during execution
- [ ] Job status updates in real-time via WebSocket
- [ ] Job can be cancelled while running
- [ ] Failed jobs can be retried
- [ ] Job appears in RunJobForm (if applicable)
- [ ] Job parameters are properly passed to backend

### Integration Tests

- [ ] Job can be triggered via API
- [ ] Job runs to completion without errors
- [ ] Progress updates appear in UI
- [ ] Multiple instances don't run simultaneously (if applicable)
- [ ] Job results are properly stored and retrievable

## Example Implementation

### Reference Jobs

Study these existing job implementations as examples:

1. **Download Jobs** (`backend/app/jobs/download_jobs.py`)
   - External service integration (qBittorrent)
   - Progress tracking with item counts
   - Error collection and reporting
   - Result initialization pattern

2. **Sync Jobs** (`backend/app/jobs/sync_jobs.py`)
   - Service initialization with settings
   - Database session management
   - Progress callback usage
   - Result status mapping

3. **Analysis Jobs** (`backend/app/jobs/analysis_jobs.py`)
   - Complex multi-step processing
   - Cancellation handling
   - Progress message parsing
   - Service initialization pattern

### Common Patterns from Reference Jobs

1. **Service Initialization**
```python
# Load settings first
settings = await load_settings_with_db_overrides()

# Initialize external services
stash_service = StashService(
    stash_url=settings.stash.url,
    api_key=settings.stash.api_key
)
```

2. **Database Session Usage**
```python
# Create session only when needed for DB operations
async with AsyncSessionLocal() as db:
    sync_service = SyncService(stash_service, db)
    result = await sync_service.sync_all(...)
```

3. **Progress Reporting**
```python
# Use the provided callback - it handles its own session
await progress_callback(0, "Starting job")
await progress_callback(50, f"Processing item {current}/{total}")
await progress_callback(100, "Job completed")
```

4. **Result Structure**
```python
# Return a dictionary with standard fields
return {
    "job_id": job_id,
    "status": "completed",  # or "failed", "cancelled", "completed_with_errors"
    "total_items": total,
    "processed_items": processed,
    "errors": errors_list,
    # Add job-specific fields
}
```

## Common Pitfalls to Avoid

1. **Don't share database sessions** between functions or store them as instance variables
2. **Don't access model attributes** after their session has closed
3. **Don't create your own progress updates** - use the provided callback
4. **Don't forget to handle cancellation** - check the cancellation token regularly
5. **Don't catch exceptions** without re-raising - let the job service handle final status
6. **Don't return model objects** from functions that create their own sessions
7. **Don't forget to refresh** objects returned from other services before accessing attributes
8. **Don't initialize services inside database sessions** - do it before or after
9. **Don't forget to close external service connections** in the finally block

## Type Hint Inconsistency Note

You may notice that existing jobs use `Callable[[int, Optional[str]], None]` for the progress_callback type hint, but the actual callback is async (`Awaitable[None]`). Use the correct async type:

```python
progress_callback: Callable[[int, Optional[str]], Awaitable[None]]
```

## Debugging Tips

1. **Check logs for session issues**: Look for "greenlet_spawn has not been called" errors
2. **Verify service initialization**: Ensure settings are loaded before creating services
3. **Test cancellation**: Use the job monitor to cancel jobs and verify cleanup
4. **Monitor WebSocket updates**: Check that progress updates appear in real-time
5. **Validate result structure**: Ensure your job returns expected fields

## Summary

Adding a new job requires:
1. Backend: Define job type, implement handler, register it
2. Frontend: Add type definitions, labels, and colors
3. Follow session management guidelines to avoid greenlet errors
4. Test thoroughly, especially concurrent execution and error cases

Key principles:
- Each database operation needs its own session scope
- Always use the provided progress callback for status updates
- Initialize services with proper settings
- Handle cancellation gracefully
- Let the job service manage final status updates