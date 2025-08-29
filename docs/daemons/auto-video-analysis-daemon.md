# Auto Video Analysis Daemon

## Overview

The Auto Video Analysis Daemon is a background process that automatically detects and analyzes video content for scenes that haven't been processed yet. It uses AI-powered video analysis to detect tags and markers from video frames and creates analysis plans for review.

## Purpose

This daemon addresses the need for automated video content analysis by:
- Continuously monitoring for scenes without video analysis
- Processing scenes in efficient batches
- Creating analysis plans with detected tags and markers
- Reducing manual effort in scene categorization

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `heartbeat_interval` | integer | 30 | Seconds between daemon heartbeat updates. Used for health monitoring. |
| `job_interval_seconds` | integer | 600 | Seconds to sleep between checking for scenes needing analysis (10 minutes default). |
| `batch_size` | integer | 50 | Number of scenes to analyze in each batch. Larger batches are more efficient but take longer to complete. |

## How It Works

### Job Checking Behavior
**NOTE:** This daemon does NOT check for system-wide active jobs before processing. It will create and monitor its own ANALYSIS jobs regardless of other running jobs in the system. The daemon uses time intervals to control when to create new jobs, not system job status.

### Step-by-Step Process

1. **Check for Pending Scenes**
   - Queries the database for scenes where `video_analyzed = false`
   - Counts total scenes needing analysis
   - If no scenes need analysis, sleeps until next interval

2. **Batch Processing**
   - Retrieves up to `batch_size` scenes for processing (default: 50)
   - Logs the current batch number and total expected batches
   - Example: "Processing batch 1 of 5 (50 scenes)"

3. **Create Video Analysis Job**
   - Creates an ANALYSIS job with specific options:
     - `detect_video_tags: true` - Enables video frame analysis
     - `detect_performers: false` - Skips performer detection
     - `detect_studios: false` - Skips studio detection
     - `detect_tags: false` - Skips text-based tag detection
     - `detect_details: false` - Skips detail generation
   - Assigns a descriptive plan name with timestamp
   - Tracks the job for monitoring

4. **Monitor Job Completion**
   - Continuously checks the status of launched analysis jobs
   - Waits for jobs to complete (COMPLETED, FAILED, or CANCELLED status)
   - Logs the final status of each job

5. **Sleep and Repeat**
   - After processing all monitored jobs
   - Logs the count of scenes processed
   - Sleeps for `job_interval_seconds` before next check
   - Process repeats indefinitely while daemon is running

## Video Analysis Details

The video analysis process:
- Extracts frames from video files at configured intervals
- Sends frames to an AI server for tag detection
- Identifies content tags and scene markers with timestamps
- Creates a structured plan of metadata changes for manual review
- Updates the scene's `video_analyzed` flag to prevent reprocessing

## Monitoring

The daemon provides several monitoring capabilities:

### Logs
- **DEBUG**: Detailed progress information
- **INFO**: Batch processing status, job creation/completion
- **WARNING**: Non-critical issues
- **ERROR**: Failed job creation or processing errors

### Health Checks
- Regular heartbeat updates every `heartbeat_interval` seconds
- Tracks uptime and last activity
- Monitors number of active jobs

### Job History
- Records all jobs launched with timestamps
- Tracks job completion status
- Maintains relationship between daemon and jobs

## Usage Examples

### Starting the Daemon

1. Navigate to the Daemons page in the UI
2. Find "Auto Video Analysis Daemon"
3. Click the Start button
4. Optionally enable Auto-start for automatic startup

### Adjusting Configuration

1. Open the daemon details page
2. Navigate to the Configuration tab
3. Modify the JSON configuration:

```json
{
  "heartbeat_interval": 30,
  "job_interval_seconds": 300,  // Check every 5 minutes
  "batch_size": 100             // Process 100 scenes at once
}
```

4. Click "Update Configuration"
5. Restart the daemon for changes to take effect

### Monitoring Progress

Check the daemon logs to see:
- How many scenes are pending analysis
- Current batch being processed
- Job IDs for tracking
- Completion status of analysis jobs

## Performance Considerations

- **Batch Size**: Larger batches (100-200) are more efficient but take longer to complete. Smaller batches (10-25) provide more frequent updates.
- **Interval**: Shorter intervals increase responsiveness but add database load. Longer intervals reduce overhead but delay processing.

## Dependencies

The daemon requires:
- Running Stash instance with API access
- AI video analysis server configured in settings
- Database with scenes table and video_analyzed column
- Proper permissions for creating and monitoring jobs

## Troubleshooting

### Daemon Not Finding Scenes
- Check that scenes exist with `video_analyzed = false`
- Verify database connection
- Review daemon logs for query errors

### Jobs Failing
- Check AI server availability and configuration
- Verify video file paths are accessible
- Review job logs for specific error messages

### Plans Not Being Applied
- Plans created by this daemon require manual review and approval
- Check the Analysis Plans page in the UI to review and apply generated plans
- Use the Auto Plan Applier Daemon if you want automatic plan application

### High Resource Usage
- Reduce `batch_size` to process fewer scenes at once
- Increase `job_interval_seconds` to reduce check frequency
- Monitor AI server load and adjust accordingly