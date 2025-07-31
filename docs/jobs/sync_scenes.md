# Sync Scenes Job

## Overview
The sync scenes job performs a targeted synchronization of specific scenes from Stash. This job always performs a full sync of the specified scenes, ensuring they are completely up-to-date.

## Job Type
`sync_scenes`

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scene_ids` | array | Yes | List of scene IDs to synchronize |

## Examples

### Sync specific scenes
```json
{
  "job_type": "sync_scenes",
  "metadata": {
    "scene_ids": ["scene123", "scene456", "scene789"]
  }
}
```

### Sync a single scene
```json
{
  "job_type": "sync_scenes",
  "metadata": {
    "scene_ids": ["scene123"]
  }
}
```

## Behavior
- Always performs a full sync of specified scenes (ignores timestamps)
- If a scene ID doesn't exist in Stash, it will be logged as an error but won't stop the job
- Progress is reported per scene
- Each scene is fully synchronized including all metadata, performers, tags, studios, etc.
- This job is typically used when:
  - You need to update specific scenes immediately
  - You're troubleshooting sync issues with particular scenes
  - The UI requests a sync of selected scenes
  - A scene was recently modified and you want to sync it without waiting for the next incremental sync

## API Endpoint
`POST /api/sync/scenes`

### Request Body
```json
{
  "scene_ids": ["scene123", "scene456"]
}
```

### Response
```json
{
  "id": "job-uuid",
  "type": "sync_scenes",
  "status": "pending",
  "progress": 0,
  "parameters": {
    "scene_ids": ["scene123", "scene456"]
  }
}
```

## UI Usage
In the StashHog UI, this job is available:
1. In the Scheduler under "Sync Scenes" with a text field for scene IDs
2. From scene list/grid views when selecting specific scenes to sync
3. From individual scene detail pages

## Performance Considerations
- This job is optimized for syncing a small number of scenes (1-100)
- For syncing all scenes, use the main `sync` job with `include_scenes: true`
- Each scene requires multiple API calls to Stash, so syncing many scenes may take time

## Migration Notes
The `force` parameter has been removed from this job type as it now always performs a full sync of the specified scenes. This ensures that when users explicitly request to sync specific scenes, they get the most up-to-date data.