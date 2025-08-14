# Download Processor Daemon

## Overview

The Download Processor Daemon automatically processes completed downloads from qBittorrent and triggers Stash metadata scans for newly added content.

## Workflow

1. **Check for Downloads**: Periodically checks qBittorrent for completed torrents with category 'xxx' that don't have the 'synced' tag
2. **Process Downloads**: If downloads are found, launches a PROCESS_DOWNLOADS job that:
   - Links/copies torrent content to `/downloads/avideos/`
   - Adds 'synced' tag to processed torrents
   - Logs each processed download with file counts
3. **Trigger Metadata Scan**: If items were successfully processed, launches a STASH_SCAN job to index the new content
4. **Sleep**: Waits for the configured interval before checking again

## Configuration

The daemon accepts the following configuration parameters:

```json
{
  "heartbeat_interval": 30,      // Seconds between heartbeat updates (default: 30)
  "job_interval_seconds": 300    // Seconds between processing checks (default: 300)
}
```

## Job Monitoring

The daemon implements comprehensive job monitoring:

- Tracks all jobs it launches (PROCESS_DOWNLOADS and STASH_SCAN)
- Logs detailed information about processed downloads including:
  - Download names
  - Number of files processed per download
  - Total files linked/copied
- Waits for jobs to complete before proceeding to next step
- Records job actions (LAUNCHED, FINISHED) for audit trail

## Logging

The daemon provides detailed logging at multiple levels:

- **INFO**: Major events (job creation, completion, download processing)
- **DEBUG**: Detailed status updates and monitoring information
- **WARNING**: Non-critical issues (missing jobs, failed items)
- **ERROR**: Critical errors with stack traces

## Error Handling

- Continues running even if individual downloads fail
- Backs off (30 seconds) on critical errors
- Logs full stack traces for debugging
- Gracefully handles shutdown signals

## Dependencies

- **qBittorrent**: Must be configured and accessible
- **Stash Server**: Must be configured for metadata scanning
- **Download Check Service**: Used to check for pending downloads
- **Job Service**: Used to create and manage jobs

## Database Record

The daemon record is created by migration `e5da50fb8835_add_download_processor_daemon_record.py` with:
- Name: "Download Processor Daemon"
- Type: "download_processor_daemon"
- Enabled: false (must be manually enabled)
- Auto-start: false

## Usage

To enable and start the daemon:

1. Enable it through the API or UI
2. Start it manually or set auto_start=true for automatic startup
3. Monitor logs through the daemon logs endpoint

## Related Components

- **Process Downloads Job**: Handles the actual download processing
- **Stash Scan Job**: Performs metadata scanning in Stash
- **Download Check Service**: Determines which downloads need processing