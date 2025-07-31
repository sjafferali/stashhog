# Sync Job

## Overview
The sync job synchronizes data from your Stash instance to StashHog. It can perform either a full resync or an incremental sync, and allows you to choose which entity types to include.

## Job Type
`sync`

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `full_resync` | boolean | false | When true, performs a complete resynchronization ignoring timestamps. When false, only syncs items modified since the last sync. |
| `include_scenes` | boolean | true | Whether to synchronize scenes |
| `include_performers` | boolean | true | Whether to synchronize performers |
| `include_tags` | boolean | true | Whether to synchronize tags |
| `include_studios` | boolean | true | Whether to synchronize studios |

## Examples

### Full sync of all entities
```json
{
  "job_type": "sync",
  "metadata": {
    "full_resync": true
  }
}
```

### Incremental sync of all entities (default)
```json
{
  "job_type": "sync",
  "metadata": {}
}
```

### Incremental sync of only performers and tags
```json
{
  "job_type": "sync",
  "metadata": {
    "full_resync": false,
    "include_scenes": false,
    "include_performers": true,
    "include_tags": true,
    "include_studios": false
  }
}
```

### Full sync of only scenes
```json
{
  "job_type": "sync",
  "metadata": {
    "full_resync": true,
    "include_scenes": true,
    "include_performers": false,
    "include_tags": false,
    "include_studios": false
  }
}
```

## Behavior
- If `full_resync` is false, the job will only sync items that have been modified since the last successful sync
- Entity types not included will be skipped entirely
- The job will sync entities in this order: performers, tags, studios, scenes
- Progress is reported throughout the sync process
- If any entity type fails to sync, the job will continue with the remaining types

## API Endpoint
`POST /api/sync`

### Request Body (optional)
```json
{
  "force": false  // Legacy parameter, maps to full_resync
}
```

### Response
```json
{
  "id": "job-uuid",
  "type": "sync",
  "status": "pending",
  "progress": 0,
  "parameters": {
    "force": false
  }
}
```

## UI Usage
In the StashHog UI, this job is available in the Scheduler under "Sync from Stash" with checkboxes for:
- Full Resync (ignore timestamps)
- Include Scenes
- Include Performers  
- Include Tags
- Include Studios

## Migration Notes
This job type replaces the previous individual sync job types:
- `sync_performers` → Use `sync` with `include_performers: true` and others false
- `sync_tags` → Use `sync` with `include_tags: true` and others false
- `sync_studios` → Use `sync` with `include_studios: true` and others false
- `sync_all` → Now just `sync`

The `force` parameter has been renamed to `full_resync` for clarity.