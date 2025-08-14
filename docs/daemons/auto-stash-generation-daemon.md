# Auto Stash Generation Daemon

## Overview

The Auto Stash Generation Daemon is a background process that automatically generates media resources (thumbnails, previews, sprites, etc.) in Stash when needed. It monitors for resources requiring generation and runs the Stash metadata generation process to ensure all media files have their associated resources properly generated.

## Purpose

This daemon addresses the need for automatic resource generation in Stash by:
- Monitoring for media files that need resource generation
- Waiting for idle periods when no other jobs are running
- Automatically triggering Stash's metadata generation process
- Ensuring all media files have thumbnails, previews, and other required resources
- Reducing manual intervention for resource generation

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `heartbeat_interval` | integer | 30 | Seconds between daemon heartbeat updates. Used for health monitoring. |
| `job_interval_seconds` | integer | 3600 | Seconds to sleep between generation checks (1 hour default). |
| `retry_interval_seconds` | integer | 3600 | Seconds to wait when other jobs are running before retrying (1 hour default). |

## How It Works

### Step-by-Step Process

1. **Check for Running Jobs**
   - Queries the job system for any running or pending jobs
   - If jobs are detected, waits for `retry_interval_seconds` before retrying
   - Continues checking until no active jobs are found
   - Ensures generation doesn't interfere with other operations

2. **Check Resource Generation Status**
   - Creates and runs a CHECK_STASH_GENERATE job
   - This job queries Stash to determine if any resources need generation
   - Waits for the check job to complete
   - Parses the result to determine if generation is needed
   - If no resources need generation, skips to step 4

3. **Run Metadata Generation**
   - If resources need generation, creates a STASH_GENERATE job
   - This job triggers Stash's metadata generation process
   - Monitors the job until completion
   - Logs the outcome (success, failure, or timeout)
   - Generation creates thumbnails, previews, sprites, and other media resources

4. **Sleep and Repeat**
   - After generation completes or if no generation was needed
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

## Monitoring

The daemon provides several monitoring capabilities:

### Logs
- **DEBUG**: No resources need generation, job progress updates
- **INFO**: Job creation, generation status, completion messages
- **WARNING**: Job failures, timeouts, or unexpected states
- **ERROR**: Service failures or generation errors

### Health Checks
- Regular heartbeat updates every `heartbeat_interval` seconds
- Tracks uptime and last activity
- Monitors active generation jobs

### Job Tracking
- Records all CHECK_STASH_GENERATE jobs launched
- Records all STASH_GENERATE jobs launched
- Tracks job completion status and timing
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
  "job_interval_seconds": 7200,  // Check every 2 hours
  "retry_interval_seconds": 1800  // Retry every 30 minutes when blocked
}
```

4. Click "Update Configuration"
5. Restart the daemon for changes to take effect

### Monitoring Generation Activity

Check the daemon logs to see:
- Whether resources need generation
- Resource counts by type (scenes, galleries, etc.)
- Generation job IDs for tracking
- Completion status of generation operations
- Wait times when other jobs are running

## Performance Considerations

- **Check Interval**: Longer intervals (3600+ seconds) reduce system load but delay resource generation. Shorter intervals increase responsiveness but add overhead.
- **Retry Interval**: When jobs are running, the retry interval prevents excessive checking. Set based on typical job duration in your system.
- **Resource Intensity**: Generation is CPU and I/O intensive. The daemon avoids running when other jobs are active to prevent system overload.
- **Storage Impact**: Generated resources consume disk space. Ensure adequate storage is available before enabling.

## Dependencies

The daemon requires:
- Running Stash instance with API access
- Valid Stash API key configured in settings
- Network connectivity to Stash server
- Sufficient disk space for generated resources
- CPU resources for video processing
- Job service for creating and monitoring jobs

## Troubleshooting

### Daemon Always Waiting for Jobs
- Check if other daemons are continuously creating jobs
- Review job history for stuck or long-running jobs
- Consider adjusting `retry_interval_seconds` for your workflow
- Verify job service is properly cleaning up completed jobs

### Generation Not Occurring
- Verify Stash API connection and credentials
- Check that CHECK_STASH_GENERATE job completes successfully
- Review Stash logs for generation errors
- Ensure Stash has permissions to write generated files
- Verify sufficient disk space is available

### Generation Jobs Failing
- Check Stash server logs for specific errors
- Verify ffmpeg and other dependencies are installed
- Review file permissions on media directories
- Check for corrupted media files preventing generation
- Ensure adequate system resources (CPU, memory)

### Excessive Generation Attempts
- Increase `job_interval_seconds` to reduce check frequency
- Verify Stash is successfully saving generated resources
- Check if new media is being added frequently
- Review if other processes are deleting generated resources

### Timeout Issues
- Generation jobs may timeout on large libraries
- Check the job timeout settings
- Consider running generation manually for initial setup
- Review Stash performance settings

## Integration with Other Features

The Auto Stash Generation Daemon works alongside:
- **Stash Scan Jobs**: New media from scans will be picked up for generation
- **Manual Generation**: Manual generation updates the resource status
- **Other Job Types**: Daemon waits for all jobs to complete before running
- **Download Processor**: Downloaded media will have resources generated
- **Scene Sync**: Synced scenes may trigger resource generation needs

## Best Practices

1. **Initial Setup**: Run manual generation first for large libraries
2. **Scheduling**: Configure to run during off-peak hours
3. **Storage Planning**: Ensure 20-30% free space for generated resources
4. **Monitoring**: Check logs regularly for generation failures
5. **Coordination**: Avoid scheduling with other resource-intensive daemons

## Resource Requirements

Typical resource usage during generation:
- **CPU**: 50-100% of available cores
- **Memory**: 1-4GB depending on video resolution
- **Disk I/O**: High read/write activity
- **Network**: Minimal (API calls only)
- **Storage**: ~10-20% of original media size for generated resources