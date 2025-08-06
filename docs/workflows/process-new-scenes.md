# Process New Scenes Workflow

## Overview

The Process New Scenes workflow is a comprehensive automated pipeline that handles newly downloaded content from initial download through to final metadata generation. This workflow orchestrates six distinct steps, each implemented as a separate sub-job for modularity and error isolation.

**Job Type**: `process_new_scenes`  
**Total Steps**: 6  
**Progress Range**: 0% to 100%

## Workflow Diagram

```
┌─────────────────┐
│   Initialize    │ (0%)
└────────┬────────┘
         │
┌────────▼────────┐
│ Step 1: Process │ (5-15%)
│   Downloads     │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 0 items │───┐
    └─────────┘   │
         │        │
┌────────▼────────┐│
│ Step 2: Stash   ││ (20-30%)
│ Metadata Scan   ││ (Skipped if no items)
└────────┬────────┘│
         │         │
         └────┬────┘
              │
┌────────────▼────┐
│ Step 3: Sync    │ (35-45%)
│  (Incremental)  │
└────────┬────────┘
         │
┌────────▼────────┐
│ Step 4: Analyze │ (50-80%)
│ Scenes (Batch)  │
└────────┬────────┘
         │
┌────────▼────────┐
│ Step 5: Generate│ (85-95%)
│    Metadata     │
└────────┬────────┘
         │
┌────────▼────────┐
│   Completed     │ (100%)
└─────────────────┘
```

## Step Details

### Step 1: Process Downloads (5-15%)

**Sub-job Type**: `process_downloads`  
**Purpose**: Processes completed downloads from qBittorrent, handling torrent management and file organization.

**What it does**:
- Connects to qBittorrent to check for completed downloads
- Processes each completed torrent (hardlinks/copies files to organized locations)
- Cleans up source files based on configuration
- Returns count of newly synced items

**Exit Conditions**:
- **Success**: Always continues (even if 0 items processed)
- **Failure**: Workflow terminates with error status
- **Special Behavior**: If 0 items were synced, Step 2 is skipped

**Key Metadata**:
```json
{
  "synced_items": 42  // Number of items processed
}
```

### Step 2: Stash Metadata Scan (20-30%)

**Sub-job Type**: `stash_scan`  
**Purpose**: Updates the Stash library to recognize newly added files.

**What it does**:
- Triggers Stash's internal scanning mechanism
- Discovers new media files in monitored directories
- Updates Stash's database with basic file information
- Prepares files for import into StashHog

**Exit Conditions**:
- **Skipped**: If Step 1 found 0 items, this step is skipped entirely
- **Success**: Continues to Step 3
- **Failure**: Workflow continues but marks status as "completed_with_errors"

**Special Cases**:
- When skipped, progress still advances to 20% with status "Skipped - No new items"
- The workflow continues normally from Step 3 onwards

### Step 3: Incremental Sync (35-45%)

**Sub-job Type**: `sync`  
**Purpose**: Imports newly discovered scenes from Stash into StashHog's database.

**What it does**:
1. **Pre-check**: Queries Stash API to check if there are any scenes pending sync
   - Checks for scenes updated since last sync completion
   - If no previous sync exists, checks total scene count
2. **Conditional Execution**:
   - If pending scenes > 0: Performs incremental sync
   - If pending scenes = 0: Skips this step entirely
3. **Sync Process** (when executed):
   - Creates Scene records in StashHog database
   - Syncs associated metadata (performers, tags, studios)
   - Marks scenes as unanalyzed for later processing
   - Updates sync timestamps

**Parameters**:
```json
{
  "force": false  // Incremental sync only
}
```

**Exit Conditions**:
- **Skipped**: If no scenes are pending sync, this step is skipped entirely
- **Success**: Continues to Step 4
- **Failure**: Workflow continues but marks status as "completed_with_errors"

**Special Cases**:
- When skipped, progress advances to 45% with status "Skipped - No pending scenes"
- The workflow continues normally from Step 4 onwards

### Step 4: Analyze Scenes (50-80%)

**Sub-job Type**: `analysis` (multiple batches)  
**Purpose**: Performs video analysis on all unanalyzed scenes to extract tags and markers.

**What it does**:
1. **Pre-check**: Queries database for scenes where `video_analyzed = false`
   - Counts total unanalyzed scenes
   - If count = 0: Skips this step entirely

2. **Batch Discovery** (when executed):
   - Groups unanalyzed scenes into batches of 100
   - Orders by newest first

3. **Per Batch Processing**:
   - Creates analysis sub-job with options:
     ```json
     {
       "detect_video_tags": true,
       "detect_performers": false,
       "detect_studios": false,
       "detect_tags": true,
       "detect_details": false
     }
     ```
   - Automatically approves all detected changes
   - Creates apply_plan sub-job to save changes

4. **Progress Calculation**:
   - Distributes 30% progress (50-80%) across all batches
   - Updates parent job with current batch info

**Exit Conditions**:
- **Skipped**: If no unanalyzed scenes found, this step is skipped entirely
- **Success**: Continues to Step 5 regardless of individual batch failures
- **Failure**: Individual batch failures are logged but don't stop workflow

**Special Cases**:
- When skipped, progress advances to 80% with status "Skipped - No unanalyzed scenes"
- The workflow continues normally from Step 5 onwards

**Batch Result Tracking**:
```json
{
  "batch_num": 1,
  "scenes_analyzed": 100,
  "changes_approved": 250,
  "changes_applied": 250,
  "errors": []
}
```

### Step 5: Generate Stash Metadata (85-95%)

**Sub-job Type**: `stash_generate`  
**Purpose**: Generates preview images, sprites, and other metadata in Stash.

**What it does**:
- Triggers Stash's preview generation for new scenes
- Creates video previews
- Generates sprite sheets for timeline scrubbing
- Extracts additional technical metadata

**Exit Conditions**:
- **Success**: Continues to completion
- **Failure**: Workflow continues but marks status as "completed_with_errors"

### Step 6: Completion (100%)

**Purpose**: Final cleanup and summary generation.

**What it does**:
- Aggregates results from all steps
- Generates final summary statistics
- Updates workflow status to "completed" or "completed_with_errors"

## Progress Reporting

The workflow uses weighted progress calculation with fixed milestones:

| Step | Progress Range | Weight |
|------|---------------|--------|
| 1 | 0-15% | 15% |
| 2 | 15-30% | 15% |
| 3 | 30-45% | 15% |
| 4 | 45-80% | 35% |
| 5 | 80-95% | 15% |
| 6 | 95-100% | 5% |

Progress is updated at step boundaries to prevent progress bar resets. Sub-job progress is shown in status messages but doesn't affect the parent job's percentage.

## Error Handling

### Cancellation
- Parent job monitors cancellation token
- Cancels active sub-job when parent is cancelled
- Cleanly exits workflow with "cancelled" status
- All database transactions are properly rolled back

### Sub-job Failures
- Individual sub-job failures don't terminate the workflow
- Failed steps are recorded in workflow result
- Final status becomes "completed_with_errors" if any step fails
- Error details preserved in step results

### Database Session Management
- Each operation uses its own database session
- Prevents SQLAlchemy greenlet errors
- Ensures proper transaction isolation

## Workflow Result Structure

```json
{
  "job_id": "workflow-uuid",
  "status": "completed|failed|cancelled|completed_with_errors",
  "steps": {
    "process_downloads": {
      "job_id": "sub-job-uuid",
      "status": "completed",
      "result": {"synced_items": 42},
      "duration_seconds": 120
    },
    "stash_scan": { /* ... */ },
    "incremental_sync": { /* ... */ },
    "analysis_batches": [
      {
        "batch_num": 1,
        "scenes_analyzed": 100,
        "changes_approved": 250,
        "changes_applied": 250,
        "errors": []
      }
    ],
    "stash_generate": { /* ... */ },
    "final_incremental_sync": { /* ... */ }
  },
  "summary": {
    "total_synced_items": 42,
    "total_scenes_analyzed": 141,
    "total_changes_approved": 350,
    "total_changes_applied": 350,
    "total_errors": 0
  }
}
```

## UI Integration

The workflow job displays a special `WorkflowJobCard` component showing:
- Step-by-step progress visualization
- Current step indicator with name
- Active sub-job details (type, status, progress)
- Overall workflow progress bar
- Expandable summary of results

## Configuration

No specific configuration required. The workflow uses existing StashHog settings:
- qBittorrent connection settings
- Stash API configuration
- Analysis options from defaults
- Batch size fixed at 100 scenes

## Workflow Behavior Notes

### Optimized Step Execution
The workflow includes intelligent pre-checks to skip unnecessary operations:

#### Step 3 (Incremental Sync)
- **Pre-check**: Queries Stash API to check for scenes updated since last sync
- **Skip condition**: No pending scenes to sync
- **Benefit**: Avoids running expensive sync operations when no changes exist

#### Step 4 (Scene Analysis)
- **Pre-check**: Queries database for scenes with `video_analyzed = false`
- **Skip condition**: No unanalyzed scenes found
- **Benefit**: Avoids creating analysis jobs when all scenes are already analyzed

### Continuing Without New Downloads
The workflow will always run to completion, even if no new items were downloaded in Step 1. This ensures that:
- Any previously unanalyzed scenes get processed in Step 4 (if they exist)
- Metadata generation runs for any scenes needing it
- The workflow provides a complete cycle regardless of new downloads

This design allows the workflow to catch up on any backlog of unprocessed content, while still being efficient by skipping steps that have no work to perform.

## Common Issues

### Workflow Not Showing Special UI
- Ensure job type is exactly "process_new_scenes"
- Check that metadata contains workflow fields
- Verify WebSocket updates include metadata

### Analysis Steps Taking Long Time
- Large number of unanalyzed scenes
- Each batch processes up to 100 scenes
- Video analysis is CPU intensive

### Downloads Not Being Processed
- Check qBittorrent connection settings
- Verify completed downloads exist
- Check file permissions

## Manual Trigger

The workflow can be triggered via API:
```bash
POST /api/jobs
{
  "job_type": "process_new_scenes"
}
```

Or programmatically:
```python
job = await job_service.create_job(
    job_type=JobType.PROCESS_NEW_SCENES,
    db=db
)
```

## Monitoring

Monitor workflow progress through:
- Jobs page UI (shows WorkflowJobCard)
- WebSocket updates on job channel
- API endpoint: `GET /api/jobs/{job_id}`
- Logs with prefix: `app.jobs.process_new_scenes_job`

## Future Enhancements

1. **Configurable Batch Sizes**: Allow tuning based on system resources
2. **Selective Step Execution**: Skip certain steps based on configuration
3. **Parallel Batch Processing**: Run multiple analysis batches concurrently
4. **Retry Logic**: Automatic retry for failed sub-jobs
5. **Scheduling**: Cron-based automatic execution