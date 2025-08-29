# Auto Plan Applier Daemon

## Overview

The Auto Plan Applier Daemon is a background process that automatically applies approved changes from analysis plans. It monitors for plans in DRAFT or REVIEWING status, filters them based on configured prefixes, and either auto-approves all changes or applies only pre-approved changes based on configuration.

## Purpose

This daemon addresses the need for automated plan application by:
- Continuously monitoring for plans ready to be applied
- Filtering plans based on name prefixes for selective processing
- Supporting both automatic approval and manual approval workflows
- Reducing manual effort in applying bulk metadata changes
- Providing flexibility in which plans get automatically processed

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `heartbeat_interval` | integer | 30 | Seconds between daemon heartbeat updates. Used for health monitoring. |
| `job_interval_seconds` | integer | 60 | Seconds to sleep between checking for plans to apply (1 minute default). |
| `plan_prefix_filter` | array | [] | List of name prefixes to filter plans. Only plans whose names start with one of these strings will be processed. **Important:** An empty array means ALL plans in DRAFT/REVIEWING status will be processed - use with caution! |
| `auto_approve_all_changes` | boolean | false | Whether to automatically approve and apply ALL changes in filtered plans. If false, only applies changes already marked as approved. |

## How It Works

### Job Checking Behavior
**NOTE:** This daemon does NOT check for system-wide active jobs before processing. It will create and monitor its own APPLY_PLAN jobs regardless of other running jobs in the system. Plans are processed sequentially - the daemon waits for each apply job to complete before moving to the next plan.

### Step-by-Step Process

1. **Check for Candidate Plans**
   - Queries the database for plans with status `DRAFT` or `REVIEWING`
   - If no plans found, sleeps until next interval
   - Logs the number of plans found

2. **Apply Prefix Filter**
   - Filters retrieved plans based on `plan_prefix_filter` configuration
   - **If filter is empty (default), ALL plans in DRAFT/REVIEWING status are considered for processing**
   - If filter has values, only plans with names starting with those prefixes are processed
   - Example: Filter `["Auto Video Analysis"]` would only process plans starting with "Auto Video Analysis"
   - To prevent processing any plans automatically, set a prefix that won't match any plan names

3. **Determine Processing Mode**
   - **If `auto_approve_all_changes = true`**:
     - Looks for ANY unapplied changes in the plan
     - Will approve and apply all changes, regardless of approval status
   - **If `auto_approve_all_changes = false`**:
     - Only looks for changes that are already approved (`status = APPROVED` or `accepted = true`)
     - Will not touch unapproved changes

4. **Check for Applicable Changes**
   - Counts the number of changes that can be applied based on the mode
   - If no applicable changes found, skips the plan
   - Logs the number of changes to be applied

5. **Create Apply Plan Job**
   - Creates an APPLY_PLAN job with appropriate settings:
     - Sets `auto_approve` flag based on configuration
     - Includes plan ID for tracking
     - Sets `created_by` to identify daemon as source
   - Tracks the job for monitoring

6. **Monitor Job Completion**
   - **IMPORTANT: The daemon processes plans sequentially** - it waits for each apply job to complete before moving to the next plan
   - This prevents concurrent modifications and ensures orderly processing
   - Continuously checks the status of the current apply job
   - Waits for job to complete (COMPLETED, FAILED, or CANCELLED status)
   - Logs the final status of each job
   - Reports any errors from failed jobs

7. **Process Results and Repeat**
   - After all filtered plans have been processed
   - Logs the count of plans processed
   - Sleeps for `job_interval_seconds` before next check
   - Process repeats indefinitely while daemon is running

## Use Cases

### Automatic Approval Workflow
For trusted sources like the Auto Video Analysis Daemon:
```json
{
  "plan_prefix_filter": ["Auto Video Analysis"],
  "auto_approve_all_changes": true,
  "job_interval_seconds": 60
}
```
This configuration automatically approves and applies all changes from video analysis.

### Manual Review Workflow
For user-generated or AI-suggested changes requiring review:
```json
{
  "plan_prefix_filter": ["User Import", "AI Suggestion"],
  "auto_approve_all_changes": false,
  "job_interval_seconds": 300
}
```
This only applies changes that users have manually approved in the UI.

### Selective Processing
To process only specific types of plans:
```json
{
  "plan_prefix_filter": ["Auto Video Analysis", "Batch Import"],
  "auto_approve_all_changes": false,
  "job_interval_seconds": 120
}
```
This processes only plans from video analysis and batch imports.

## Monitoring

The daemon provides several monitoring capabilities:

### Logs
- **DEBUG**: Detailed filtering and processing information
- **INFO**: Plan processing status, job creation/completion, count of plans processed
- **WARNING**: Non-critical issues
- **ERROR**: Failed job creation, processing errors, or job failures

### Health Checks
- Regular heartbeat updates every `heartbeat_interval` seconds
- Tracks uptime and last activity
- Monitors number of active apply jobs

### Job History
- Records all apply jobs launched with timestamps
- Tracks job completion status
- Maintains relationship between daemon, jobs, and plans

## Usage Examples

### Starting the Daemon

1. Navigate to the Daemons page in the UI
2. Find "Auto Plan Applier Daemon"
3. Click the Start button
4. Optionally enable Auto-start for automatic startup

### Adjusting Configuration

1. Open the daemon details page
2. Navigate to the Configuration tab
3. Modify the JSON configuration:

```json
{
  "heartbeat_interval": 30,
  "job_interval_seconds": 120,
  "plan_prefix_filter": [
    "Auto Video Analysis",
    "Batch Import - ",
    "Manual Upload"
  ],
  "auto_approve_all_changes": true
}
```

4. Click "Update Configuration"
5. Restart the daemon for changes to take effect

### Monitoring Progress

Check the daemon logs to see:
- How many plans match the filter criteria
- Which plans are being processed
- Job IDs for tracking apply operations
- Success/failure status of apply jobs
- Count of changes applied per plan

## Performance Considerations

- **Check Interval**: Shorter intervals (30-60s) provide faster response to new plans but increase database load. Longer intervals (300-600s) reduce overhead.
- **Auto-approval**: Enabling auto-approval processes plans faster but removes the review step. Use with caution for untrusted sources.
- **Prefix Filtering**: Using specific prefixes reduces the number of plans checked, improving performance and providing better control. **An empty filter will process ALL plans!**
- **Sequential Processing**: The daemon processes plans one at a time, waiting for each apply job to complete before starting the next. This ensures orderly processing but means large batches of plans will take longer to complete.

## Integration with Other Daemons

### Auto Video Analysis Daemon
The Auto Plan Applier works well with the Auto Video Analysis Daemon:
1. Video Analysis Daemon creates plans with prefix "Auto Video Analysis"
2. Plan Applier configured with this prefix automatically applies the changes
3. Provides end-to-end automation of video analysis workflow

### Example Combined Configuration
Video Analysis Daemon creates plans, Plan Applier applies them:
```json
{
  "plan_prefix_filter": ["Auto Video Analysis - "],
  "auto_approve_all_changes": true,
  "job_interval_seconds": 60
}
```

## Dependencies

The daemon requires:
- Database with analysis_plan and plan_change tables
- Job service for creating and monitoring apply jobs
- Proper permissions for querying plans and creating jobs
- Stash API access for applying changes

## Troubleshooting

### Daemon Not Finding Plans
- Verify plans exist with status `DRAFT` or `REVIEWING`
- Check that plan names match configured prefixes
- Review daemon logs for query results
- Ensure database connection is working

### Plans Not Being Applied
- Verify `auto_approve_all_changes` setting matches your workflow
- Check that plans have unapplied changes
- For manual approval mode, ensure changes are marked as approved
- Review apply job logs for specific errors

### Jobs Failing
- Check Stash API availability
- Verify scene IDs in plans still exist
- Review job result errors in daemon logs
- Check for conflicting changes in plans

### Wrong Plans Being Processed
- Review `plan_prefix_filter` configuration
- Check plan names in database
- Consider using more specific prefixes
- Monitor logs to see which plans match filters

### High Database Load
- Increase `job_interval_seconds` to reduce check frequency
- Use specific prefix filters to reduce plans checked
- Monitor number of plans in DRAFT/REVIEWING status
- Consider archiving old applied plans