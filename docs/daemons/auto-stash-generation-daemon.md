# Auto Stash Generation Daemon

## Overview

The Auto Stash Generation Daemon is a background process that automatically generates media resources (thumbnails, previews, sprites, etc.) in Stash for scenes that are missing them. It monitors scenes with the `generated` attribute set to false and runs the Stash metadata generation process to ensure all media files have their associated resources properly generated.

## Purpose

This daemon addresses the need for automatic resource generation in Stash by:
- Monitoring for scenes with the `generated` attribute set to false
- Waiting for idle periods when no other jobs are running
- Automatically triggering Stash's metadata generation process
- Monitoring generation jobs and cancelling them if scan jobs are detected
- Ensuring all media files have thumbnails, previews, and other required resources
- Reducing manual intervention for resource generation

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `heartbeat_interval` | integer | 30 | Seconds between daemon heartbeat updates. Used for health monitoring. |
| `job_interval_seconds` | integer | 3600 | Seconds to sleep between generation cycles (1 hour default). |

## How It Works

### Step-by-Step Process

1. **Check for Running Jobs** ⚠️ **IMPORTANT: This daemon checks for ALL active jobs**
   - Queries the job system for ANY running or pending jobs (all job types)
   - If ANY jobs are detected (SYNC, ANALYSIS, APPLY_PLAN, etc.), skips the generation check entirely
   - Sleeps for the full `job_interval_seconds` (default: 3600 seconds) before checking again
   - This is the ONLY daemon that performs this system-wide job check
   - Ensures generation doesn't interfere with any other operations in the system

2. **Check for Scenes Missing Generated Attribute**
   - Queries the database for scenes where `generated=false`
   - If all scenes have `generated=true`, skips to step 4
   - Logs the count of scenes needing generation

3. **Start and Monitor Stash Generate Metadata Job**
   - Creates a STASH_GENERATE job to trigger Stash's metadata generation process
   - Enters a monitoring loop that runs every 30 seconds:
     a. Checks if the generation job has completed (success, failure, or cancelled)
     b. Checks for any STASH_SCAN jobs in running or pending status
     c. If scan jobs are detected, cancels the generation job to avoid conflicts
     d. Continues monitoring until the job completes
   - Reports the final status of the generation job

4. **Sleep and Repeat**
   - After the generation cycle completes
   - Sleeps for `job_interval_seconds` (default: 3600 seconds)
   - Process repeats indefinitely while daemon is running

## Resource Generation Details

The Stash metadata generation process creates:
- **Thumbnails**: Static preview images for scenes
- **Preview Videos**: Short video clips for quick preview
- **Sprites**: Image strips for video timeline scrubbing
- **Markers**: Visual markers for specific timestamps
- **Transcodes**: Alternative video formats if configured
- **Hashes**: Perceptual hashes for duplicate detection

When all resources are successfully generated for a scene, the `generated` attribute is automatically set to `true` by the STASH_GENERATE job.

## Monitoring

The daemon provides several monitoring capabilities:

### Logs
- **DEBUG**: All scenes have generated attribute set, job progress updates
- **INFO**: Job creation, scenes needing generation count, scan job detection, cancellation events
- **WARNING**: Job failures or unexpected states
- **ERROR**: Service failures or generation errors

### Health Checks
- Regular heartbeat updates every `heartbeat_interval` seconds
- Tracks uptime and last activity
- Monitors active generation jobs

### Job Tracking
- Records all STASH_GENERATE jobs launched
- Tracks job cancellations due to scan job conflicts
- Records job completion status and timing
- Maintains audit trail of generation operations

## Usage Examples

### Starting the Daemon

1. Navigate to the Daemons page in the UI
2. Find "Auto Stash Generation Daemon"
3. Click the Start button
4. Optionally enable Auto-start for automatic startup

### Adjusting Configuration

1. Open the daemon details page
2. Navigate to the Configuration tab
3. Modify the JSON configuration:

```json
{
  "heartbeat_interval": 30,
  "job_interval_seconds": 7200  // Check every 2 hours
}
```

4. Click "Update Configuration"
5. Restart the daemon for changes to take effect

### Monitoring Generation Activity

Check the daemon logs to see:
- Count of scenes with `generated=false`
- Generation job IDs for tracking
- Progress updates during generation
- Detection and cancellation of jobs when scan jobs appear
- Completion status of generation operations
- Skip messages when all scenes are already generated

## Performance Considerations

- **Check Interval**: Longer intervals (3600+ seconds) reduce system load but delay resource generation. Shorter intervals increase responsiveness but add overhead.
- **Scan Job Detection**: The daemon monitors for scan jobs every 30 seconds during generation and will cancel generation to prioritize scanning operations.
- **Resource Intensity**: Generation is CPU and I/O intensive. The daemon avoids running when other jobs are active to prevent system overload.
- **Storage Impact**: Generated resources consume disk space. Ensure adequate storage is available before enabling.
- **Database Queries**: The daemon efficiently checks for scenes with `generated=false` to minimize database load.

## Dependencies

The daemon requires:
- Running Stash instance with API access
- Valid Stash API key configured in settings
- Network connectivity to Stash server
- Sufficient disk space for generated resources
- CPU resources for video processing
- Job service for creating and monitoring jobs

## Troubleshooting

### Daemon Skipping Generation
- Check if other jobs are running or pending
- Verify scenes have `generated=false` in the database
- Review daemon logs for "All scenes have generated attribute set" messages
- Ensure the CHECK_STASH_GENERATE job is properly updating the `generated` attribute

### Generation Jobs Being Cancelled
- This is normal behavior when scan jobs are detected
- The daemon prioritizes scan operations over generation
- Generation will resume in the next cycle after scan completes
- Check logs for "Detected X scan jobs, cancelling generation job" messages

### Generation Not Occurring
- Verify Stash API connection and credentials
- Check that scenes exist with `generated=false`
- Review Stash logs for generation errors
- Ensure Stash has permissions to write generated files
- Verify sufficient disk space is available

### Generation Jobs Failing
- Check Stash server logs for specific errors
- Verify ffmpeg and other dependencies are installed
- Review file permissions on media directories
- Check for corrupted media files preventing generation
- Ensure adequate system resources (CPU, memory)

### All Scenes Already Generated
- This is the expected state when all resources are complete
- The daemon will continue monitoring for new scenes
- Scenes will have `generated=false` after:
  - New scenes are added
  - Markers are modified during sync
  - Manual updates to the `generated` attribute

### Timeout Issues
- Generation jobs may timeout on large libraries
- Check the job timeout settings
- Consider running generation manually for initial setup
- Review Stash performance settings

## Integration with Other Features

The Auto Stash Generation Daemon works alongside:
- **Stash Scan Jobs**: Generation jobs will be cancelled if scan jobs are detected to avoid conflicts
- **CHECK_STASH_GENERATE Job**: Updates the `generated` attribute for scenes based on resource completeness
- **STASH_GENERATE Job**: Sets `generated=true` for scenes after successful resource generation
- **Scene Sync**: Marker changes during sync automatically set `generated=false` for affected scenes
- **Manual Generation**: Manual generation through the UI will update the `generated` attribute
- **Other Job Types**: Daemon waits for all jobs to complete before starting generation

## Best Practices

1. **Initial Setup**: Run CHECK_STASH_GENERATE job first to properly set the `generated` attribute
2. **Scheduling**: Configure `job_interval_seconds` based on your library update frequency
3. **Storage Planning**: Ensure 20-30% free space for generated resources
4. **Monitoring**: Check logs regularly for cancellation events and generation failures
5. **Coordination**: The daemon automatically handles job conflicts by cancelling when scan jobs appear
6. **Database Maintenance**: Periodically verify the `generated` attribute accuracy with CHECK_STASH_GENERATE job

## Resource Requirements

Typical resource usage during generation:
- **CPU**: 50-100% of available cores during generation
- **Memory**: 1-4GB depending on video resolution
- **Disk I/O**: High read/write activity during generation
- **Database**: Minimal queries (checking for `generated=false` scenes)
- **Network**: Minimal (API calls only)
- **Storage**: ~10-20% of original media size for generated resources