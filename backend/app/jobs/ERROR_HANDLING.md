# Job Error Handling Guidelines

## Overview

This document outlines the error handling patterns for background jobs in StashHog. Jobs can handle errors in two ways: re-raising exceptions for complete failures or returning error results for partial failures.

## Error Handling Patterns

### 1. Re-raise Exceptions (Complete Failure) → Job Status: `FAILED`

**When to use:**
- Service initialization failures (e.g., missing API keys, invalid configuration)
- Database connection failures
- Critical errors that prevent any work from being done

**Pattern:**
```python
try:
    # Create services
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(...)
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise  # Re-raise for complete failure
```

**UI Display:** Shows red failed status with error in job.error field

### 2. Return Error Results (Partial Success) → Job Status: `COMPLETED` with errors

**When to use:**
- Batch operations where some items succeed and some fail
- Operations that can partially complete
- When detailed error reporting is needed

**Pattern:**
```python
job_result = {
    "processed": 100,
    "successful": 85,
    "failed": 15,
    "errors": [
        {"item_id": "123", "error": "Timeout"},
        {"item_id": "456", "error": "Invalid format"}
    ]
}

# Set status hint for job service
if all_failed:
    job_result["status"] = "failed"
elif errors:
    job_result["status"] = "completed_with_errors"

return job_result
```

**UI Display:** Shows green completed status with error details in result

## Job-Specific Guidelines

### Sync Jobs (`sync_jobs.py`)

- **Initialization errors**: Re-raise (complete failure)
- **Individual item sync failures**: Return in errors array
- **Status mapping**:
  - `SyncStatus.FAILED` → `"status": "failed"`
  - `SyncStatus.PARTIAL` → `"status": "completed_with_errors"`
  - `SyncStatus.SUCCESS` → Normal completion

### Analysis Jobs (`analysis_jobs.py`)

- **analyze_scenes_job**: Re-raises for critical errors (maintains backward compatibility)
- **apply_analysis_plan_job**: Returns error result for all failures
- **generate_scene_details_job**: Per-item error tracking with status summary

### Cleanup Jobs (`cleanup_jobs.py`)

- Always returns error results (cleanup is best-effort)
- Tracks errors for each cleanup operation
- Continues processing even if some operations fail

## Status Field Convention

Jobs can include a `status` field in their result to hint at the overall job status:

- `"status": "failed"` - Job should be marked as FAILED
- `"status": "completed_with_errors"` - Job completed but had errors
- `"status": "completed"` - Job completed successfully

## Error Result Structure

Always include an `errors` array in the result for operations that can have partial failures:

```python
{
    "errors": [
        {
            "type": "sync_error",
            "entity_id": "scene_123",
            "error": "Scene not found in Stash"
        }
    ]
}
```

## Best Practices

1. **Be consistent within operation types** - Similar operations should handle errors similarly
2. **Include context in errors** - Always include item IDs, operation types, etc.
3. **Log before returning/raising** - Use logger.error() with exc_info=True
4. **Progress callback on failure** - Update progress to 100% with error message
5. **Graceful degradation** - Continue processing other items after individual failures