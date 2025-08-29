# Auto Stash Sync Daemon

## Overview

The Auto Stash Sync Daemon is a background process that automatically monitors and synchronizes scenes that have been updated in Stash. It ensures that changes made in your Stash instance are reflected in StashHog by performing incremental syncs when needed.

## Purpose

This daemon addresses the need for keeping StashHog synchronized with Stash by:
- Continuously monitoring for scenes that have been updated in Stash since the last sync
- Performing incremental syncs to capture only changed content
- Reducing manual sync operations
- Ensuring data consistency between Stash and StashHog

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `heartbeat_interval` | integer | 30 | Seconds between daemon heartbeat updates. Used for health monitoring. |
| `job_interval_seconds` | integer | 300 | Seconds to sleep between checking for pending scenes (5 minutes default). |

## How It Works

### Job Checking Behavior
**NOTE:** This daemon does NOT check for system-wide active jobs before processing. It will create and monitor its own SYNC jobs regardless of other running jobs in the system. Each sync job is monitored to completion before checking for new pending scenes.

### Step-by-Step Process

1. **Check for Pending Scenes**
   - Queries Stash API to find scenes updated since the last sync
   - Uses the last successful sync timestamp as a reference point
   - If no previous sync exists, counts all scenes as pending
   - Skips to sleep if no scenes need syncing

2. **Create Incremental Sync Job**
   - When pending scenes are detected, creates a SYNC job
   - The job performs an incremental sync (not a full resync)
   - Metadata includes the number of pending scenes for tracking
   - Job is marked as created by "AUTO_STASH_SYNC_DAEMON"

3. **Monitor Job Completion**
   - Tracks the created sync job until completion
   - Waits for job to reach COMPLETED, FAILED, or CANCELLED status
   - Logs the outcome with details about scenes synced

4. **Log Sync Execution**
   - Upon successful completion: "Executed incremental sync due to X scenes that needed to be resynced"
   - Upon failure: Logs warning with job status
   - Tracks job action as FINISHED in daemon job history

5. **Sleep and Repeat**
   - After job completion or if no scenes need syncing
   - Sleeps for `job_interval_seconds` (default: 300 seconds)
   - Process repeats indefinitely while daemon is running

## Sync Details

The incremental sync process:
- Fetches only scenes modified after the last sync timestamp
- Updates scene metadata including title, details, ratings, and dates
- Preserves local modifications where appropriate
- Updates related entities (performers, tags, studios) as needed
- Records sync history for audit purposes

## Monitoring

The daemon provides several monitoring capabilities:

### Logs
- **DEBUG**: No scenes pending sync
- **INFO**: Found X scenes pending sync, job creation, sync execution
- **WARNING**: Job failures or unexpected states
- **ERROR**: Service initialization failures or sync errors

### Health Checks
- Regular heartbeat updates every `heartbeat_interval` seconds
- Tracks uptime and last activity
- Monitors active sync jobs

### Job History
- Records all sync jobs launched with timestamps
- Tracks job completion status
- Maintains audit trail of sync operations

## Usage Examples

### Starting the Daemon

1. Navigate to the Daemons page in the UI
2. Find "Auto Stash Sync Daemon"
3. Click the Start button
4. Optionally enable Auto-start for automatic startup

### Adjusting Configuration

1. Open the daemon details page
2. Navigate to the Configuration tab
3. Modify the JSON configuration:

```json
{
  "heartbeat_interval": 30,
  "job_interval_seconds": 600  // Check every 10 minutes
}
```

4. Click "Update Configuration"
5. Restart the daemon for changes to take effect

### Monitoring Sync Activity

Check the daemon logs to see:
- Number of scenes pending sync from Stash
- Sync job IDs for tracking
- Completion status of sync operations
- Timing of incremental syncs

## Performance Considerations

- **Check Interval**: Shorter intervals (60-300 seconds) provide faster sync but increase API calls. Longer intervals (600-1800 seconds) reduce load but delay synchronization.
- **Incremental vs Full**: The daemon always performs incremental syncs to minimize processing time and network usage.
- **Concurrent Jobs**: The daemon waits for each sync job to complete before checking for new changes, preventing job overlap.

## Dependencies

The daemon requires:
- Running Stash instance with API access
- Valid Stash API key configured in settings
- Network connectivity to Stash server
- Database with sync history tracking
- Dashboard status service for pending scene detection

## Troubleshooting

### Daemon Not Finding Pending Scenes
- Verify Stash API connection and credentials
- Check that scenes exist in Stash
- Review last sync timestamp in sync history
- Ensure Dashboard Status Service is functioning

### Sync Jobs Failing
- Check Stash server availability
- Verify API key permissions
- Review network connectivity
- Check job logs for specific error messages

### Excessive Sync Operations
- Increase `job_interval_seconds` to reduce check frequency
- Verify that Stash webhook notifications aren't triggering additional syncs
- Check for automated processes modifying scenes in Stash

### No Syncs Occurring Despite Changes
- Ensure daemon is running (check status)
- Verify last sync timestamp is being updated
- Check timezone configuration between Stash and StashHog
- Review daemon logs for initialization errors

## Integration with Other Features

The Auto Stash Sync Daemon works alongside:
- **Manual Sync Operations**: Manual syncs update the last sync timestamp used by this daemon
- **Scene-specific Syncs**: Individual scene syncs don't affect the daemon's incremental sync detection
- **Other Daemons**: Can trigger analysis daemons after successful sync completion
- **Sync History**: All syncs are recorded in the sync history table for auditing