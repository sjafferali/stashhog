# Auto Video Analysis Daemon

## Overview

The Auto Video Analysis Daemon is a background process that automatically detects and analyzes video content for scenes that haven't been processed yet. It uses AI-powered video analysis to detect tags and markers from video frames, then creates and applies analysis plans to update scene metadata.

## Purpose

This daemon addresses the need for automated video content analysis by:
- Continuously monitoring for scenes without video analysis
- Processing scenes in efficient batches
- Automatically applying detected tags and markers
- Reducing manual effort in scene categorization

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `heartbeat_interval` | integer | 30 | Seconds between daemon heartbeat updates. Used for health monitoring. |
| `job_interval_seconds` | integer | 600 | Seconds to sleep between checking for scenes needing analysis (10 minutes default). |
| `batch_size` | integer | 50 | Number of scenes to analyze in each batch. Larger batches are more efficient but take longer to complete. |
| `auto_approve_plans` | boolean | true | Whether to automatically approve and apply generated analysis plans. If false, plans will be created but require manual approval. |

## How It Works

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

5. **Handle Analysis Results**
   - If a job completes successfully and generates a plan:
     - Retrieves the plan ID from the job results
     - Checks if the plan has already been applied
     - If `auto_approve_plans = true`, proceeds to apply the plan

6. **Apply Analysis Plan**
   - Creates an APPLY_PLAN job with auto-approval
   - Monitors the apply job until completion
   - Updates scene metadata with detected tags and markers

7. **Sleep and Repeat**
   - After processing all monitored jobs
   - Logs the count of scenes processed
   - Sleeps for `job_interval_seconds` before next check
   - Process repeats indefinitely while daemon is running

## Video Analysis Details

The video analysis process:
- Extracts frames from video files at configured intervals
- Sends frames to an AI server for tag detection
- Identifies content tags and scene markers with timestamps
- Creates a structured plan of metadata changes
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
  "batch_size": 100,            // Process 100 scenes at once
  "auto_approve_plans": false   // Require manual approval
}
```

4. Click "Update Configuration"
5. Restart the daemon for changes to take effect

### Monitoring Progress

Check the daemon logs to see:
- How many scenes are pending analysis
- Current batch being processed
- Job IDs for tracking
- Completion status of analysis and apply jobs

## Performance Considerations

- **Batch Size**: Larger batches (100-200) are more efficient but take longer to complete. Smaller batches (10-25) provide more frequent updates.
- **Interval**: Shorter intervals increase responsiveness but add database load. Longer intervals reduce overhead but delay processing.
- **Auto-approval**: Disabling auto-approval allows review of detected tags but requires manual intervention to apply changes.

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
- Ensure `auto_approve_plans` is set to `true`
- Check for existing plans in PENDING status
- Verify apply job creation in logs

### High Resource Usage
- Reduce `batch_size` to process fewer scenes at once
- Increase `job_interval_seconds` to reduce check frequency
- Monitor AI server load and adjust accordingly