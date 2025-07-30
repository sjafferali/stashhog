# Adding New Workflow Jobs to StashHog

This guide explains how to create workflow jobs that orchestrate multiple sub-jobs, with special attention to progress reporting and avoiding greenlet errors.

## Table of Contents

1. [What are Workflow Jobs?](#what-are-workflow-jobs)
2. [Architecture Overview](#architecture-overview)
3. [Implementation Guide](#implementation-guide)
4. [Progress Reporting](#progress-reporting)
5. [Metadata Requirements](#metadata-requirements)
6. [Avoiding Greenlet Errors](#avoiding-greenlet-errors)
7. [Frontend Integration](#frontend-integration)
8. [Example Implementation](#example-implementation)
9. [Testing Workflow Jobs](#testing-workflow-jobs)
10. [Troubleshooting](#troubleshooting)

## What are Workflow Jobs?

Workflow jobs are special job types that:
- Orchestrate multiple sub-jobs in a defined sequence
- Provide unified progress tracking across all steps
- Handle complex multi-stage operations
- Report detailed status for each step

The `process_new_scenes` job is an example that runs 6 distinct steps: download processing, metadata scanning, syncing, analysis, applying changes, and metadata generation.

## Architecture Overview

### Key Components

1. **Main Workflow Handler**: Orchestrates the entire workflow
2. **Sub-job Creation**: Creates and monitors individual jobs
3. **Progress Aggregation**: Combines progress from all steps
4. **Metadata Tracking**: Maintains workflow state and sub-job information
5. **Frontend Display**: Special UI component for workflow visualization

### Workflow Structure

```python
workflow_job
├── Step 1: Sub-job A
├── Step 2: Sub-job B
├── Step 3: Sub-job C (may include multiple batches)
│   ├── Batch 1
│   ├── Batch 2
│   └── Batch N
└── Step N: Final sub-job
```

## Implementation Guide

### 1. Basic Workflow Template

```python
"""Your workflow job description."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.core.database import AsyncSessionLocal
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


async def your_workflow_job(
    job_id: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute your workflow job.
    
    IMPORTANT: This is a workflow job that creates and monitors sub-jobs.
    Follow these guidelines:
    1. Each sub-job must use its own database session
    2. Update parent job metadata with current step info
    3. Use weighted progress calculation
    4. Handle cancellation across all sub-jobs
    """
    logger.info(f"Starting workflow job {job_id}")
    
    # Initialize result tracking
    workflow_result: Dict[str, Any] = {
        "job_id": job_id,
        "status": "completed",
        "steps": {},
        "summary": {
            "total_items_processed": 0,
            "total_errors": 0,
            # Add workflow-specific summary fields
        },
    }
    
    # Define step weights for progress calculation
    STEP_WEIGHTS = {
        1: (0, 20),     # Step 1: 0-20%
        2: (20, 50),    # Step 2: 20-50%
        3: (50, 90),    # Step 3: 50-90%
        4: (90, 100),   # Step 4: 90-100%
    }
    
    try:
        # Initial progress
        await progress_callback(0, "Starting workflow")
        
        # Get job service
        from app.core.dependencies import get_job_service
        job_service = get_job_service()
        
        # Step 1
        await progress_callback(5, "Step 1/4: First operation")
        step1_result = await _run_workflow_step(
            job_service,
            JobType.YOUR_SUB_JOB_TYPE,
            {"param1": "value1"},
            job_id,
            "First Operation",
            progress_callback,
            cancellation_token,
            workflow_result,
            "step1",
            {"current_step": 1, "total_steps": 4},
        )
        
        if not step1_result or step1_result["status"] != "completed":
            workflow_result["status"] = "completed_with_errors"
            return workflow_result
        
        # Continue with more steps...
        
        # Final progress
        await progress_callback(100, "Workflow completed")
        
        return workflow_result
        
    except asyncio.CancelledError:
        logger.info(f"Workflow {job_id} was cancelled")
        workflow_result["status"] = "cancelled"
        raise
    except Exception as e:
        error_msg = f"Workflow failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        workflow_result["status"] = "failed"
        workflow_result["error"] = error_msg
        raise
```

### 2. Sub-job Creation and Monitoring

```python
async def _create_and_run_subjob(
    job_service: JobService,
    job_type: JobType,
    metadata: Dict[str, Any],
    parent_job_id: str,
    step_name: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    step_info: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Create and run a sub-job, polling until completion.
    
    CRITICAL: Each database operation MUST use its own session to avoid greenlet errors.
    """
    logger.info(f"Starting {step_name} for parent job {parent_job_id}")
    
    # Check if already cancelled before creating sub-job
    if cancellation_token and cancellation_token.is_cancelled:
        logger.info(f"Skipping {step_name} - workflow already cancelled")
        return None
    
    # Create sub-job with its own session
    async with AsyncSessionLocal() as db:
        sub_job = await job_service.create_job(
            job_type=job_type,
            db=db,
            metadata={**metadata, "parent_job_id": parent_job_id},
        )
        await db.commit()
        sub_job_id = str(sub_job.id)
    
    # Update parent job metadata with current sub-job info
    if step_info:
        async with AsyncSessionLocal() as db:
            parent_job = await job_service.get_job(parent_job_id, db)
            if parent_job:
                parent_metadata = parent_job.job_metadata or {}
                parent_metadata.update({
                    "current_step": step_info.get("current_step", 1),
                    "total_steps": step_info.get("total_steps", 1),
                    "step_name": step_name,
                    "active_sub_job": {
                        "id": sub_job_id,
                        "type": job_type.value,
                        "status": "running",
                        "progress": 0,
                    },
                })
                parent_job.job_metadata = parent_metadata
                await db.commit()
    
    # Poll for completion
    poll_interval = 2  # seconds
    while True:
        # Check cancellation
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Parent job {parent_job_id} cancelled, stopping {step_name}")
            async with AsyncSessionLocal() as db:
                await job_service.cancel_job(sub_job_id, db)
                await db.commit()
            return None
        
        # Check sub-job status with new session
        async with AsyncSessionLocal() as db:
            sub_job_result = await job_service.get_job(sub_job_id, db)
            if not sub_job_result:
                logger.error(f"Sub-job {sub_job_id} not found")
                return None
            sub_job = sub_job_result
            
            # Update parent metadata with sub-job progress
            parent_job = await job_service.get_job(parent_job_id, db)
            if parent_job and parent_job.job_metadata:
                parent_metadata = parent_job.job_metadata
                if "active_sub_job" in parent_metadata:
                    parent_metadata["active_sub_job"]["status"] = sub_job.status.value
                    parent_metadata["active_sub_job"]["progress"] = sub_job.progress
                    parent_job.job_metadata = parent_metadata
                    await db.commit()
            
            if sub_job.is_finished():
                logger.info(f"Sub-job {sub_job_id} finished with status: {sub_job.status}")
                
                # Clear active sub-job from parent metadata
                if parent_job and parent_job.job_metadata and "active_sub_job" in parent_job.job_metadata:
                    parent_metadata = parent_job.job_metadata
                    parent_metadata["active_sub_job"] = None
                    parent_job.job_metadata = parent_metadata
                    await db.commit()
                
                return {
                    "job_id": sub_job_id,
                    "status": sub_job.status.value if hasattr(sub_job.status, "value") else sub_job.status,
                    "result": sub_job.result,
                    "error": sub_job.error,
                    "duration_seconds": sub_job.get_duration_seconds(),
                }
            
            # Update progress message (don't change percentage)
            raw_metadata = sub_job.job_metadata
            job_metadata: Dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
            await progress_callback(
                None,  # Don't change progress percentage
                f"{step_name}: {job_metadata.get('message', 'In progress...')}",
            )
        
        await asyncio.sleep(poll_interval)
```

### 3. Workflow Step Helper

```python
async def _run_workflow_step(
    job_service: JobService,
    job_type: JobType,
    metadata: Dict[str, Any],
    parent_job_id: str,
    step_name: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    workflow_result: Dict[str, Any],
    result_key: str,
    step_info: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Run a workflow step and update results."""
    # Check if already cancelled before creating sub-job
    if cancellation_token and cancellation_token.is_cancelled:
        logger.info(f"Skipping {step_name} - workflow already cancelled")
        return None
        
    result = await _create_and_run_subjob(
        job_service,
        job_type,
        metadata,
        parent_job_id,
        step_name,
        progress_callback,
        cancellation_token,
        step_info,
    )
    
    workflow_result["steps"][result_key] = result
    
    if not result or result["status"] != "completed":
        workflow_result["status"] = "completed_with_errors"
        workflow_result["summary"]["total_errors"] += 1
    
    return result
```

## Progress Reporting

### Weighted Progress Calculation

Workflow jobs should use weighted progress to ensure smooth progress across all steps. The current implementation uses **manual progress reporting** at specific points:

```python
# Define step weights (for future smooth progress implementation)
STEP_WEIGHTS = {
    1: (0, 15),     # Step 1: 0-15%
    2: (15, 30),    # Step 2: 15-30%
    3: (30, 80),    # Step 3: 30-80% (larger step)
    4: (80, 95),    # Step 4: 80-95%
    5: (95, 100),   # Step 5: 95-100%
}

# Current implementation: Manual progress points
await progress_callback(5, "Step 1/6: Processing downloads")
await progress_callback(20, "Step 2/6: Scanning metadata")
await progress_callback(35, "Step 3/6: Running incremental sync")
await progress_callback(50, "Step 4/6: Analyzing scenes")
await progress_callback(85, "Step 5/6: Generating metadata")
await progress_callback(100, "Workflow completed")
```

**Note**: The current implementation prevents progress bar resets by using fixed percentages. For smoother intra-step progress, see `/plans/smoother_workflow_step_progress.md`.

### Progress Callback Notes

1. **Type Signature**: `Callable[[Optional[int], Optional[str]], Awaitable[None]]`
   - First parameter: Progress percentage (0-100) or None to keep current
   - Second parameter: Optional status message

2. **Message Updates**: You can update just the message without changing progress:
   ```python
   await progress_callback(None, "Processing batch 5/10")
   ```

3. **Sub-job Progress**: Don't update parent progress directly from sub-job monitoring. The current implementation correctly passes `None` for progress when monitoring sub-jobs:
   ```python
   await progress_callback(
       None,  # Don't change progress
       f"{step_name}: {job_metadata.get('message', 'In progress...')}",
   )
   ```

4. **Avoid Setting 100% on Cancellation**: Only set progress to 100% when the workflow actually completes:
   ```python
   # Final progress - only set to 100% if we actually completed
   if workflow_result["status"] == "completed" or workflow_result["status"] == "completed_with_errors":
       await progress_callback(100, "Workflow completed")
   ```

## Metadata Requirements

### Parent Job Metadata Structure

```python
{
    "current_step": 2,              # Current step number (1-based)
    "total_steps": 6,               # Total number of steps
    "step_name": "Metadata Scan",   # Human-readable step name
    "active_sub_job": {             # Currently running sub-job
        "id": "abc-123",
        "type": "stash_scan",
        "status": "running",
        "progress": 45
    },
    "message": "Scanning 1500 files..."  # Optional status message
}
```

### Workflow Result Structure

```python
{
    "job_id": "workflow-123",
    "status": "completed",  # or "failed", "cancelled", "completed_with_errors"
    "steps": {
        "step1": {
            "job_id": "sub-job-1",
            "status": "completed",
            "result": {...},
            "duration_seconds": 120
        },
        "step2": {
            "job_id": "sub-job-2",
            "status": "completed",
            "result": {...},
            "duration_seconds": 300
        }
    },
    "summary": {
        "total_items_processed": 150,
        "total_errors": 0,
        # Add workflow-specific summary fields
    }
}
```

## Avoiding Greenlet Errors

### Critical Rules for Workflow Jobs

1. **Each Database Operation Needs Its Own Session**
   ```python
   # ✅ CORRECT: New session for each operation
   async with AsyncSessionLocal() as db:
       parent_job = await job_service.get_job(parent_job_id, db)
       # Update and commit
       await db.commit()
   
   # ❌ WRONG: Reusing sessions
   db = some_external_session  # Never do this
   ```

2. **Don't Pass Sessions Between Functions**
   ```python
   # ✅ CORRECT: Each function creates its own session
   async def update_parent_metadata(job_id: str, metadata: dict):
       async with AsyncSessionLocal() as db:
           job = await job_service.get_job(job_id, db)
           job.job_metadata = metadata
           await db.commit()
   
   # ❌ WRONG: Passing session as parameter
   async def update_parent_metadata(db: AsyncSession, job_id: str, metadata: dict):
       # This can cause greenlet errors
   ```

3. **Progress Callbacks Are Session-Independent**
   ```python
   # ✅ CORRECT: Use the provided callback
   await progress_callback(50, "Processing...")
   
   # ❌ WRONG: Manual job updates
   async with AsyncSessionLocal() as db:
       job = await db.get(Job, job_id)
       job.progress = 50  # Don't do this
   ```

4. **Handle Service Returns Properly**
   ```python
   # When job_service returns objects created in different sessions
   job = await job_service.create_job(...)
   
   # ✅ CORRECT: Refresh if needed
   await db.refresh(job)
   
   # ❌ WRONG: Direct attribute access might fail
   job_id = job.id  # May cause greenlet error
   ```

5. **Complete Operations Before Session Closes**
   ```python
   # ✅ CORRECT: Access all needed data while session is active
   async with AsyncSessionLocal() as db:
       job = await job_service.get_job(job_id, db)
       metadata = job.job_metadata  # Access while session is open
       await db.commit()
   
   # Now safe to use metadata outside session
   process_metadata(metadata)
   ```

6. **Clean Up Resources on Cancellation**
   ```python
   # If your workflow creates pending resources (like analysis plans),
   # clean them up in the cancellation handler:
   except asyncio.CancelledError:
       logger.info(f"Workflow {job_id} was cancelled")
       workflow_result["status"] = "cancelled"
       # Clean up any pending resources
       await _cleanup_pending_plans(job_id)
       raise
   ```

7. **Use Eager Loading for Relationships**
   ```python
   # When fetching entities with relationships, use eager loading to avoid
   # lazy loading issues after session closes:
   async with AsyncSessionLocal() as db:
       scenes = await db.execute(
           select(Scene).options(
               selectinload(Scene.performers),
               selectinload(Scene.studio),
               selectinload(Scene.tags)
           )
       )
       scenes_list = scenes.scalars().all()
       
       # Access relationships while session is active
       for scene in scenes_list:
           performer_count = len(scene.performers)  # Safe
   ```

### Common Greenlet Error Scenarios in Workflows

1. **Cross-Session Sub-job Updates**
   - Problem: Updating parent job from sub-job context
   - Solution: Each update uses its own session

2. **Lazy Loading After Polling**
   - Problem: Accessing sub-job attributes after polling session closes
   - Solution: Extract needed data while session is active

3. **Shared State Between Steps**
   - Problem: Passing SQLAlchemy objects between workflow steps
   - Solution: Pass primitive values (IDs, dicts) instead

## Frontend Integration

### 1. Update Job Type Definitions

Add your workflow job type to `frontend/src/utils/jobUtils.ts`:

```typescript
export type JobType =
  // ... existing types ...
  | 'your_workflow_job';

export const JOB_TYPE_LABELS: Record<string, string> = {
  // ... existing labels ...
  your_workflow_job: 'Your Workflow Process',
};

export const JOB_TYPE_COLORS: Record<string, string> = {
  // ... existing colors ...
  your_workflow_job: 'purple',  // Workflows often use purple
};

// Special handling for workflow progress display
export const formatJobProgress = (
  type: string,
  processed: number | undefined,
  total: number | undefined,
  progress: number
): string => {
  if (type === 'your_workflow_job') {
    return ' steps';  // Shows "Step 3/6 steps"
  }
  // ... rest of function
};
```

### 2. WorkflowJobCard Integration

The `WorkflowJobCard` component automatically displays workflow jobs with:
- Step-by-step progress visualization
- Current step indicator
- Sub-job details
- Overall progress bar

To enable it for your workflow:

```typescript
// In JobCard.tsx
if (job.type === 'your_workflow_job' && !compact) {
  return (
    <WorkflowJobCard
      job={job}
      onCancel={onCancel}
      onRetry={onRetry}
      onDelete={onDelete}
    />
  );
}
```

### 3. Update TypeScript Type Definitions

Ensure the Job metadata type in `frontend/src/types/models.ts` supports workflow metadata:

```typescript
metadata?: Record<string, string | number | boolean | null | Record<string, any>> & {
  // ... existing fields ...
  // Workflow job metadata
  current_step?: number;
  total_steps?: number;
  step_name?: string;
  active_sub_job?: {
    id: string;
    type: string;
    status: string;
    progress: number;
  };
  message?: string;
};
```

### 4. Customize Workflow Steps Display (Optional)

The default `WorkflowJobCard` uses a generic 6-step workflow. For custom steps, modify the component:

```typescript
// Currently hardcoded in WorkflowJobCard.tsx:
const WORKFLOW_STEPS = [
  { title: 'Process Downloads', description: 'Download and sync new content' },
  { title: 'Scan Metadata', description: 'Update Stash library metadata' },
  { title: 'Incremental Sync', description: 'Import new scenes' },
  { title: 'Analyze Scenes', description: 'Process unanalyzed scenes' },
  { title: 'Generate Metadata', description: 'Create previews and sprites' },
  { title: 'Complete', description: 'Workflow finished' },
];
```

## Example Implementation

### Complete Workflow Example: Data Import Workflow

```python
"""Data import workflow that processes files through multiple stages."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.core.database import AsyncSessionLocal
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


async def data_import_workflow(
    job_id: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Import data through validation, processing, and indexing stages."""
    logger.info(f"Starting data import workflow {job_id}")
    
    # Extract parameters
    import_path = kwargs.get("import_path", "")
    validate_only = kwargs.get("validate_only", False)
    
    # Initialize result
    workflow_result: Dict[str, Any] = {
        "job_id": job_id,
        "status": "completed",
        "steps": {},
        "summary": {
            "total_files": 0,
            "valid_files": 0,
            "processed_files": 0,
            "indexed_files": 0,
            "total_errors": 0,
        },
    }
    
    # Step weights
    STEP_WEIGHTS = {
        1: (0, 20),     # Validation: 0-20%
        2: (20, 60),    # Processing: 20-60%
        3: (60, 90),    # Indexing: 60-90%
        4: (90, 100),   # Cleanup: 90-100%
    }
    
    try:
        from app.core.dependencies import get_job_service
        job_service = get_job_service()
        
        # Step 1: Validate files
        await progress_callback(5, "Step 1/4: Validating import files")
        
        validation_result = await _run_workflow_step(
            job_service,
            JobType.VALIDATE_IMPORT,
            {"path": import_path},
            job_id,
            "File Validation",
            progress_callback,
            cancellation_token,
            workflow_result,
            "validation",
            {"current_step": 1, "total_steps": 4},
        )
        
        if not validation_result:
            return workflow_result
        
        valid_files = validation_result.get("result", {}).get("valid_files", 0)
        workflow_result["summary"]["total_files"] = validation_result.get("result", {}).get("total_files", 0)
        workflow_result["summary"]["valid_files"] = valid_files
        
        if valid_files == 0:
            await progress_callback(100, "No valid files to import")
            return workflow_result
        
        if validate_only:
            await progress_callback(100, f"Validation complete: {valid_files} valid files")
            return workflow_result
        
        # Step 2: Process files
        await progress_callback(25, f"Step 2/4: Processing {valid_files} files")
        
        process_result = await _run_workflow_step(
            job_service,
            JobType.PROCESS_IMPORT,
            {"file_list": validation_result.get("result", {}).get("file_list", [])},
            job_id,
            "File Processing",
            progress_callback,
            cancellation_token,
            workflow_result,
            "processing",
            {"current_step": 2, "total_steps": 4},
        )
        
        if process_result:
            workflow_result["summary"]["processed_files"] = process_result.get("result", {}).get("processed_files", 0)
        
        # Step 3: Index processed data
        await progress_callback(65, "Step 3/4: Indexing imported data")
        
        index_result = await _run_workflow_step(
            job_service,
            JobType.INDEX_DATA,
            {"process_job_id": process_result.get("job_id") if process_result else None},
            job_id,
            "Data Indexing",
            progress_callback,
            cancellation_token,
            workflow_result,
            "indexing",
            {"current_step": 3, "total_steps": 4},
        )
        
        if index_result:
            workflow_result["summary"]["indexed_files"] = index_result.get("result", {}).get("indexed_count", 0)
        
        # Step 4: Cleanup
        await progress_callback(92, "Step 4/4: Cleaning up temporary files")
        
        await _run_workflow_step(
            job_service,
            JobType.CLEANUP_TEMP,
            {"import_path": import_path},
            job_id,
            "Cleanup",
            progress_callback,
            cancellation_token,
            workflow_result,
            "cleanup",
            {"current_step": 4, "total_steps": 4},
        )
        
        # Final status
        await progress_callback(100, "Import workflow completed")
        
        logger.info(
            f"Data import workflow completed: "
            f"{workflow_result['summary']['processed_files']}/{workflow_result['summary']['total_files']} files processed"
        )
        
        return workflow_result
        
    except asyncio.CancelledError:
        logger.info(f"Workflow {job_id} was cancelled")
        workflow_result["status"] = "cancelled"
        raise
    except Exception as e:
        error_msg = f"Import workflow failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        workflow_result["status"] = "failed"
        workflow_result["error"] = error_msg
        raise


def register_data_import_workflow(job_service: JobService) -> None:
    """Register the data import workflow handler."""
    job_service.register_handler(JobType.DATA_IMPORT_WORKFLOW, data_import_workflow)
    logger.info("Registered data import workflow handler")
```

## Testing Workflow Jobs

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

async def test_workflow_creates_subjobs():
    """Test that workflow creates expected sub-jobs."""
    # Mock job service
    job_service = MagicMock()
    job_service.create_job = AsyncMock(return_value=MagicMock(
        id="sub-job-1",
        status=MagicMock(value="completed"),
        progress=100,
        job_metadata={},
        is_finished=MagicMock(return_value=True),
        result={"processed": 10}
    ))
    
    # Mock progress callback
    progress_callback = AsyncMock()
    
    # Run workflow
    result = await your_workflow_job(
        job_id="test-workflow",
        progress_callback=progress_callback,
        param1="value1"
    )
    
    # Verify sub-jobs were created
    assert job_service.create_job.call_count >= 3  # At least 3 steps
    
    # Verify progress was reported
    progress_callback.assert_any_call(0, "Starting workflow")
    progress_callback.assert_any_call(100, "Workflow completed")
    
    # Verify result structure
    assert result["status"] == "completed"
    assert "steps" in result
    assert "summary" in result
```

### Integration Tests

```python
async def test_workflow_handles_subjob_failure():
    """Test workflow behavior when a sub-job fails."""
    # Create a workflow that will have a failing sub-job
    result = await create_and_run_test_workflow(
        force_step2_failure=True
    )
    
    assert result["status"] == "completed_with_errors"
    assert result["summary"]["total_errors"] > 0
    assert result["steps"]["step2"]["status"] == "failed"
```

### Testing Greenlet Safety

```python
async def test_workflow_session_isolation():
    """Verify each operation uses its own session."""
    # This test would monitor session creation/closure
    # and verify no session is reused across operations
    pass
```

## Troubleshooting

### Common Issues

1. **Progress Bar Resets**
   - Cause: Not using weighted progress calculation
   - Solution: Implement proper step weights

2. **Sub-job Status Not Visible**
   - Cause: Parent metadata not updated
   - Solution: Update `active_sub_job` in parent metadata

3. **Greenlet Errors in Polling**
   - Cause: Reusing sessions or accessing lazy attributes
   - Solution: Create new session for each poll iteration

4. **Workflow Continues After Sub-job Failure**
   - Cause: Not checking sub-job result status
   - Solution: Check `result["status"] != "completed"`

### Debug Logging

Add detailed logging to track workflow execution:

```python
logger.debug(f"Step {step_num}: Creating sub-job {job_type}")
logger.debug(f"Sub-job {sub_job_id} progress: {progress}%")
logger.debug(f"Workflow {job_id} overall progress: {overall_progress}%")
```

### Monitoring Checklist

- [ ] All sub-jobs complete successfully
- [ ] Progress advances smoothly without resets
- [ ] Parent job metadata updates correctly
- [ ] No greenlet errors in logs
- [ ] Cancellation works at any step
- [ ] Frontend displays current step and sub-job

## Best Practices

1. **Keep Steps Atomic**: Each step should be independently retryable
2. **Save State Between Steps**: Use workflow result to track completed work
3. **Handle Partial Success**: Use "completed_with_errors" status
4. **Provide Detailed Summary**: Include counts and error details
5. **Test Each Step Independently**: Ensure sub-jobs work standalone
6. **Document Step Dependencies**: Clear prerequisites for each step
7. **Use Consistent Naming**: Step names should be clear and descriptive
8. **Monitor Resource Usage**: Long workflows may accumulate resources

## Summary

Workflow jobs provide a powerful way to orchestrate complex multi-step operations. Key requirements:

- **Metadata Structure**: Track current step, total steps, and active sub-job
- **Progress Reporting**: Use weighted calculation and don't reset between steps
- **Session Management**: Each database operation needs its own session
- **Error Handling**: Handle failures gracefully with detailed status
- **Frontend Integration**: Use WorkflowJobCard for enhanced visualization

Following these guidelines ensures your workflow jobs integrate seamlessly with the StashHog job system while providing excellent user feedback and avoiding common pitfalls like greenlet errors.