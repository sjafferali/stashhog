# Daemon Status Updates Implementation Plan

## Overview

A new real-time status reporting system has been implemented for daemons to provide visibility into what each daemon is currently doing. This document describes the system and provides a plan for updating all existing daemons to use it.

## What Was Implemented

### 1. Backend Infrastructure

#### Database Changes
- Added new fields to the `daemons` table:
  - `current_status` (String, 500 chars) - Human-readable description of current activity
  - `current_job_id` (String, 36 chars) - Optional ID of job being monitored
  - `current_job_type` (String, 100 chars) - Optional type of job being monitored
  - `status_updated_at` (DateTime) - Timestamp of last status update

#### BaseDaemon Enhancement
- Added `update_status()` method to BaseDaemon class:
  ```python
  async def update_status(
      self, 
      status_message: str, 
      job_id: Optional[str] = None, 
      job_type: Optional[str] = None
  )
  ```
- Status is automatically cleared when daemon stops
- Updates are broadcast via WebSocket for real-time UI updates

### 2. Frontend Display

#### UI Features
- Real-time status display on the Daemons page
- Shows current activity message with timestamp
- Displays job type tag and "View Job" link when job info is provided
- Updates via WebSocket without page refresh
- Clean, informative alert-style display

## Daemons That Need Updates

All existing daemons should be updated to report their status. Here are the daemons and specific areas where status reporting should be added:

### 1. AutoStashGenerationDaemon (`app/daemons/auto_stash_generation_daemon.py`)

**Key Status Points:**
- When checking for running jobs: `"Checking for running jobs"`
- When jobs are found: `"Jobs are running, sleeping for X seconds"`
- When checking for ungenerated scenes: `"Checking for scenes needing generation"`
- When no scenes need generation: `"All scenes generated, sleeping for X seconds"`
- When starting generation: `"Starting metadata generation for X scenes"`
- When monitoring generation job: `"Generating metadata"` with job_id and job_type
- When scan jobs detected: `"Cancelling generation due to scan jobs"`

### 2. AutoPlanApplierDaemon (`app/daemons/auto_plan_applier_daemon.py`)

**Key Status Points:**
- When checking for plans: `"Checking for plans to apply"`
- When filtering plans: `"Found X plans, filtering by prefix"`
- When processing a plan: `"Processing plan: [plan_name]"`
- When applying a plan: `"Applying plan ID X"` with job_id and job_type
- When waiting for job: `"Waiting for plan application to complete"`
- When sleeping: `"No plans to process, sleeping for X seconds"`

### 3. AutoStashSyncDaemon (`app/daemons/auto_stash_sync_daemon.py`)

**Key Status Points:**
- When checking for pending scenes: `"Checking for scenes to sync"`
- When no scenes need sync: `"No pending scenes, sleeping for X seconds"`
- When creating sync job: `"Syncing X scenes from Stash"`
- When monitoring sync: `"Syncing scenes"` with job_id and job_type
- When sync completes: `"Sync completed for X scenes"`

### 4. AutoVideoAnalysisDaemon (`app/daemons/auto_video_analysis_daemon.py`)

**Key Status Points:**
- When checking for scenes: `"Checking for scenes needing video analysis"`
- When processing batch: `"Processing batch X of Y (Z scenes)"`
- When creating analysis job: `"Analyzing video tags for X scenes"` with job_id and job_type
- When monitoring job: `"Analyzing video content"`
- When applying plan: `"Applying analysis plan"` with job_id and job_type
- When sleeping: `"No scenes to analyze, sleeping for X seconds"`

### 5. DownloadProcessorDaemon (`app/daemons/download_processor_daemon.py`)

**Key Status Points:**
- When checking downloads: `"Checking qBittorrent for new downloads"`
- When no downloads: `"No new downloads, sleeping for X seconds"`
- When processing downloads: `"Processing X downloads"` with job_id and job_type
- When triggering scan: `"Triggering Stash metadata scan"` with job_id and job_type
- When monitoring jobs: `"Waiting for download processing to complete"`

## Implementation Guidelines

### Where to Add Status Updates

1. **At the Start of Main Loop Iterations**
   ```python
   async def run(self):
       while self.is_running:
           await self.update_status("Checking for work")
           # ... rest of loop
   ```

2. **Before Long-Running Operations**
   ```python
   await self.update_status("Fetching data from API")
   data = await fetch_data()  # May take several seconds
   ```

3. **When Starting Jobs**
   ```python
   job = await create_job(...)
   await self.update_status(
       f"Processing job for {item_name}",
       job_id=str(job.id),
       job_type=JobType.ANALYSIS.value
   )
   ```

4. **During Sleep/Wait Periods**
   ```python
   await self.update_status(f"No work found, sleeping for {interval} seconds")
   await asyncio.sleep(interval)
   ```

5. **When Processing Items**
   ```python
   for i, item in enumerate(items, 1):
       await self.update_status(f"Processing item {i} of {len(items)}: {item.name}")
       # ... process item
   ```

### Best Practices

1. **Be Specific and Informative**
   - Include counts: `"Processing 25 scenes"`
   - Include progress: `"Processing batch 3 of 5"`
   - Include identifiers: `"Applying plan ID 12345"`

2. **Update Frequently During Long Operations**
   - Don't let status go stale during long-running tasks
   - Update at least every 30-60 seconds during active processing

3. **Include Job Information When Available**
   - Always pass job_id and job_type when monitoring jobs
   - This enables the UI to show job links

4. **Use Consistent Language**
   - "Checking for..." when looking for work
   - "Processing..." when actively working
   - "Waiting for..." when monitoring
   - "Sleeping for..." when idle

## Testing the Updates

After updating each daemon:

1. **Start the daemon** and observe the Daemons page
2. **Verify status appears** in the UI within 1-2 seconds
3. **Check job links** work when job info is provided
4. **Confirm status clears** when daemon stops
5. **Test WebSocket updates** by watching status change in real-time

## Migration Steps

For each daemon:

1. **Add status updates** at key points identified above
2. **Test locally** to ensure status messages are clear and timely
3. **Verify job information** is passed correctly
4. **Check for performance impact** (status updates are async and lightweight)
5. **Deploy and monitor** the updated daemon

## Example Implementation

Here's an example of updating a daemon's main loop:

```python
async def run(self):
    config = self._load_config()
    
    while self.is_running:
        try:
            # Report checking status
            await self.update_status("Checking for pending items")
            
            items = await self._get_pending_items()
            
            if not items:
                # Report idle status
                await self.update_status(
                    f"No items found, sleeping for {config['interval']} seconds"
                )
                await asyncio.sleep(config['interval'])
                continue
            
            # Report processing status
            await self.update_status(f"Found {len(items)} items to process")
            
            for i, item in enumerate(items, 1):
                # Report item-specific status
                await self.update_status(
                    f"Processing item {i} of {len(items)}: {item.name}"
                )
                
                # If creating a job, include job details
                job = await self._create_job(item)
                await self.update_status(
                    f"Monitoring job for {item.name}",
                    job_id=str(job.id),
                    job_type=JobType.PROCESS.value
                )
                
                # Monitor the job
                await self._monitor_job(job.id)
            
            # Report completion
            await self.update_status(f"Completed processing {len(items)} items")
            
        except Exception as e:
            await self.log(LogLevel.ERROR, f"Error: {str(e)}")
            await self.update_status("Error occurred, retrying...")
```

## Benefits of Implementation

1. **User Visibility**: Users can see exactly what each daemon is doing
2. **Debugging**: Easier to identify where daemons are stuck or slow
3. **Job Tracking**: Direct links from daemon status to related jobs
4. **Real-time Updates**: WebSocket ensures immediate status visibility
5. **Professional UI**: Clean, informative display of daemon activity

## Priority Order

Suggested order for updating daemons (by impact/usage):

1. **AutoVideoAnalysisDaemon** - Most user-facing, processes many items
2. **AutoStashSyncDaemon** - Critical for data consistency
3. **AutoPlanApplierDaemon** - Applies analysis results
4. **DownloadProcessorDaemon** - Handles new content
5. **AutoStashGenerationDaemon** - Background metadata generation

## Notes

- The status reporting system is designed to be lightweight and non-blocking
- Status updates are stored in the database and broadcast via WebSocket
- The UI automatically subscribes to daemon updates when the page loads
- Status is automatically cleared when a daemon stops
- The system is backward compatible - daemons without status updates still work normally