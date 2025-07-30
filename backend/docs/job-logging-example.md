# Job Context Logging

This document describes the automatic job context logging system implemented in StashHog.

## Overview

When jobs are executed, all log messages automatically include job context information:
- **job_type**: The type of job being executed (e.g., `sync_scenes`, `analysis`)
- **job_id**: The unique ID of the current job
- **parent_job_id**: For subjobs in workflows, the ID of the parent workflow job

## How It Works

1. **Automatic Context**: When a job is executed through the JobService, a logging context is automatically established.

2. **Transparent to Job Implementations**: Job implementations don't need to change - they continue using standard logging:
   ```python
   logger.info("Starting scene sync")  # Automatically includes job context
   ```

3. **Subjob Support**: When workflow jobs create subjobs, the parent job ID is automatically tracked.

## Log Output Examples

### Regular Job
```
2024-01-15 10:23:45 - app.jobs.sync_jobs - INFO [job_type=sync_scenes, job_id=abc123] - Starting sync_scenes job abc123 for 50 scenes
2024-01-15 10:23:46 - app.jobs.sync_jobs - INFO [job_type=sync_scenes, job_id=abc123] - Synced 10/50 scenes
```

### Workflow Job with Subjobs
```
# Parent workflow job
2024-01-15 10:30:00 - app.jobs.process_new_scenes - INFO [job_type=process_new_scenes, job_id=workflow456] - Starting process_new_scenes job workflow456

# Subjob within workflow
2024-01-15 10:30:05 - app.jobs.download_jobs - INFO [job_type=process_downloads, job_id=sub789, parent_job_id=workflow456] - Processing downloads from qBittorrent
```

### JSON Logging Format
When JSON logging is enabled, job context appears as separate fields:
```json
{
  "timestamp": "2024-01-15 10:23:45",
  "level": "INFO",
  "logger": "app.jobs.sync_jobs",
  "message": "Starting sync_scenes job abc123 for 50 scenes",
  "job_type": "sync_scenes",
  "job_id": "abc123",
  "parent_job_id": null
}
```

## Benefits

1. **Easier Debugging**: Filter logs by job_id to see all messages from a specific job execution
2. **Workflow Tracing**: Track subjob execution within workflows using parent_job_id
3. **Performance Analysis**: Analyze job execution patterns by job_type
4. **No Code Changes**: Existing job implementations automatically benefit

## Implementation Details

The system uses Python's `contextvars` to maintain job context across async boundaries. This ensures:
- Thread-safe context management
- Proper context isolation between concurrent jobs
- Automatic context propagation to all code called within a job

## For Developers

### New Job Implementation
No changes needed! Just use standard logging:

```python
async def my_new_job(job_id: str, progress_callback: Callable, **kwargs):
    logger.info("Starting my job")  # Automatically includes context
    # ... job implementation ...
```

### Manual Context (Advanced)
In rare cases where you need to manually set job context:

```python
from app.core.job_context import job_logging_context

with job_logging_context(job_id="manual123", job_type="manual_job"):
    logger.info("This will include job context")
```