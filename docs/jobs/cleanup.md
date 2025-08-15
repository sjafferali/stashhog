# Cleanup Job Documentation

## Overview

The cleanup job (`JobType.CLEANUP`) is responsible for maintaining system hygiene by purging old data, cleaning up stale jobs, and fixing inconsistent states. It performs multiple cleanup operations in a single job execution.

## Job Details

- **Job Type**: `CLEANUP`
- **Handler**: `cleanup_stale_jobs` in `backend/app/jobs/cleanup_jobs.py:287`
- **Category**: Maintenance
- **Color**: Magenta
- **Timeout**: 5 minutes
- **Concurrent Execution**: Not allowed

## What Gets Purged

### 1. Old Job History
- **Target**: Completed, failed, and cancelled jobs
- **Retention Period**: 30 days (hardcoded)
- **Criteria**: `Job.completed_at < (current_time - 30 days)`
- **Location**: `backend/app/jobs/cleanup_jobs.py:44-69`

### 2. Download History
- **Target**: Handled download records
- **Retention Period**: 14 days (hardcoded)
- **Criteria**: `HandledDownload.timestamp < (current_time - 14 days)`
- **Location**: `backend/app/jobs/cleanup_jobs.py:72-95`

### 3. Stale Job Detection
- **Target**: Jobs marked as RUNNING/PENDING but actually stuck
- **Timeout Thresholds**:
  - SYNC: 30 minutes
  - SYNC_SCENES: 30 minutes
  - ANALYSIS: 60 minutes
  - APPLY_PLAN: 30 minutes
  - GENERATE_DETAILS: 45 minutes
  - EXPORT: 15 minutes
  - IMPORT: 15 minutes
  - CLEANUP: 5 minutes
  - DEFAULT: 30 minutes
- **Location**: `backend/app/jobs/cleanup_jobs.py:18-37`

### 4. Stuck Analysis Plans
- **Target**: Plans in PENDING status with non-running jobs
- **Action**: Reset to DRAFT status
- **Location**: `backend/app/jobs/cleanup_jobs.py:98-151`

## Scheduling

### Infrastructure
- **Scheduler Class**: `SyncScheduler` in `backend/app/services/sync/scheduler.py`
- **Method**: `schedule_cleanup_job(interval_minutes=30)`
- **Default Interval**: 30 minutes
- **Grace Time**: 5 minutes for misfires

### Current Status
⚠️ **Not Automatically Scheduled**: Despite having scheduling infrastructure, the cleanup job is **not automatically scheduled** during application startup. It must be triggered manually.

### Manual Execution
The cleanup job can be triggered through:
- API endpoint: `POST /api/jobs/run` with `job_type: "cleanup"`
- Job service: `job_service.create_job(JobType.CLEANUP)`

## Process Flow

1. **Initialization** (`cleanup_stale_jobs`)
   - Create database session
   - Set current timestamp
   - Report progress: "Finding stale jobs..."

2. **Stale Job Processing**
   - Query all RUNNING/PENDING jobs
   - Check each job against timeout thresholds
   - Verify if associated task is actually running
   - Mark timed-out jobs as FAILED or COMPLETED
   - Progress: 20-90%

3. **Old Job Cleanup**
   - Delete completed/failed/cancelled jobs older than 30 days
   - Progress: 90%

4. **Download Log Cleanup**
   - Delete handled_downloads older than 14 days
   - Progress: 92%

5. **Stuck Plan Cleanup**
   - Find PENDING plans with non-running jobs
   - Reset to DRAFT status
   - Progress: 95%

6. **Completion**
   - Commit all changes
   - Return summary statistics
   - Progress: 100%

## Configuration

### Hardcoded Values
All retention periods and timeouts are **hardcoded** in the source code:

```python
# Job retention (30 days)
old_job_cutoff = current_time - timedelta(days=30)

# Download log retention (14 days)  
old_download_cutoff = current_time - timedelta(days=14)

# Job timeouts by type
JOB_TIMEOUT_MINUTES = {
    JobType.SYNC: 30,
    JobType.ANALYSIS: 60,
    # ... etc
}
```

### No Runtime Configuration
- Cannot be configured via environment variables
- Cannot be configured via settings
- Requires code changes to modify retention periods

## Return Data

The cleanup job returns detailed statistics:

```json
{
  "status": "completed|completed_with_errors|failed",
  "cleaned_jobs": 5,
  "cleaned_job_details": [
    {
      "job_id": "uuid",
      "job_type": "sync",
      "status": "failed",
      "timeout_minutes": 30,
      "elapsed_minutes": 45.2
    }
  ],
  "old_jobs_deleted": 12,
  "old_downloads_deleted": 8,
  "stuck_plans_updated": 3,
  "errors": []
}
```

## Error Handling

- **Individual Failures**: Logged but don't stop the process
- **Database Errors**: Cause job failure
- **Cancellation Support**: Respects cancellation tokens
- **Graceful Degradation**: Partial cleanup if some operations fail

## Performance Considerations

- **Database Impact**: Multiple queries and deletes
- **Transaction Safety**: Uses database transactions
- **Progress Reporting**: Real-time updates during execution
- **Cancellation**: Can be cancelled mid-execution

## Limitations

1. **Not Automatically Scheduled**: Must be triggered manually
2. **Hardcoded Configuration**: Cannot adjust retention periods without code changes
3. **No Selective Cleanup**: All cleanup operations run together
4. **No Preview Mode**: Cannot see what would be deleted without running

## Future Improvements

1. **Automatic Scheduling**: Enable default cleanup schedule
2. **Configurable Retention**: Allow runtime configuration of retention periods
3. **Selective Operations**: Allow running individual cleanup operations
4. **Preview Mode**: Show cleanup candidates without deleting
5. **Metrics**: Export cleanup statistics for monitoring

## Related Files

- **Handler**: `backend/app/jobs/cleanup_jobs.py`
- **Scheduler**: `backend/app/services/sync/scheduler.py`
- **Job Registry**: `backend/app/core/job_registry.py`
- **Models**: `backend/app/models/job.py`, `backend/app/models/handled_download.py`
- **Tests**: `backend/tests/test_cleanup_jobs.py`