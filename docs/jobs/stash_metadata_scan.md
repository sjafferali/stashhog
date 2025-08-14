# Stash Metadata Scan Job

## Overview
The Stash metadata scan job triggers a metadata scan operation on your Stash server. This scans the configured paths for new or changed media files and generates various metadata components like thumbnails, previews, sprites, and perceptual hashes.

## Job Type
`stash_scan`

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `paths` | array[string] | ["/data"] | Paths to scan on the Stash server |
| `rescan` | boolean | false | When true, rescans all files even if already in database |
| `scanGenerateCovers` | boolean | true | Generate cover images for videos |
| `scanGeneratePreviews` | boolean | true | Generate preview videos |
| `scanGenerateImagePreviews` | boolean | false | Generate previews for image files |
| `scanGenerateSprites` | boolean | true | Generate sprite sheets for video timeline |
| `scanGeneratePhashes` | boolean | true | Generate perceptual hashes for duplicate detection |
| `scanGenerateThumbnails` | boolean | false | Generate thumbnail images |
| `scanGenerateClipPreviews` | boolean | false | Generate preview clips |

## Examples

### Default scan with all standard metadata
```json
{
  "job_type": "stash_scan",
  "metadata": {}
}
```

### Rescan all files
```json
{
  "job_type": "stash_scan",
  "metadata": {
    "rescan": true
  }
}
```

### Scan specific paths
```json
{
  "job_type": "stash_scan",
  "metadata": {
    "paths": ["/media/videos", "/media/new"],
    "rescan": false
  }
}
```

### Minimal scan (only covers and phashes)
```json
{
  "job_type": "stash_scan",
  "metadata": {
    "scanGenerateCovers": true,
    "scanGeneratePreviews": false,
    "scanGenerateSprites": false,
    "scanGeneratePhashes": true,
    "scanGenerateThumbnails": false
  }
}
```

## Behavior
- The job triggers a metadata scan on the Stash server and monitors its progress
- Progress updates are provided throughout the scanning process
- The job completes when the Stash server scan finishes
- If `rescan` is true, all files will be rescanned regardless of existing metadata

## Important Cancellation Behavior

⚠️ **CRITICAL**: Unlike other StashHog jobs that interact with Stash, the metadata scan job has special cancellation handling to prevent data corruption:

- **When cancelled**: The StashHog job will be marked as cancelled, but the Stash server scan will **continue running**
- **Why**: Interrupting a metadata scan can lead to incomplete metadata or database corruption on the Stash server
- **What happens**: 
  - A warning is logged: "Cancellation requested for metadata scan job {id}, but NOT cancelling Stash server job to prevent data corruption"
  - The StashHog job status becomes "cancelled"
  - The Stash server continues the scan to completion
  - The message indicates: "StashHog job cancelled (Stash server job continues to prevent data corruption)"

This behavior is intentionally different from other Stash jobs (like generate jobs) which safely cancel the server-side operation when cancelled.

## API Endpoint
This job is typically triggered through the job queue API rather than a dedicated endpoint.

### Create Job Request
`POST /api/jobs`

```json
{
  "type": "stash_scan",
  "metadata": {
    "rescan": false,
    "scanGenerateCovers": true,
    "scanGeneratePreviews": true
  }
}
```

### Response
```json
{
  "id": "job-uuid",
  "type": "stash_scan",
  "status": "pending",
  "progress": 0,
  "metadata": {
    "rescan": false,
    "scanGenerateCovers": true,
    "scanGeneratePreviews": true
  }
}
```

## UI Usage
In the StashHog UI, this job can be triggered from:
- The Jobs page under "Stash Operations"
- The Settings page under "Media Management"

Options typically include:
- Rescan existing files checkbox
- Path selection (if multiple paths configured)
- Metadata generation options (covers, previews, sprites, etc.)

## Performance Considerations
- Metadata scanning can be resource-intensive on the Stash server
- Preview generation uses significant CPU for video encoding
- Perceptual hash generation requires processing entire video files
- Consider running during off-peak hours for large libraries
- The scan cannot be safely interrupted once started

## Related Jobs
- `stash_generate` - Generates missing metadata for existing database entries
- `sync` - Synchronizes Stash database content to StashHog after scanning