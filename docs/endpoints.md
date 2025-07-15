# StashHog API Endpoints Documentation

This document provides a comprehensive overview of all API endpoints available in the StashHog backend service.

## Base URL
All endpoints are prefixed with `/api/v1` (based on API router configuration).

## Table of Contents
- [Health Endpoints](#health-endpoints)
- [Scene Endpoints](#scene-endpoints)
- [Analysis Endpoints](#analysis-endpoints)
- [Job Endpoints](#job-endpoints)
- [Settings Endpoints](#settings-endpoints)
- [Sync Endpoints](#sync-endpoints)
- [Entity Endpoints](#entity-endpoints)

---

## Health Endpoints
**Prefix:** `/health`

### GET /health/
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /health/ready
Comprehensive readiness check for all services.

**Dependencies:**
- Database connection
- Stash service
- OpenAI service (optional)

**Response:**
```json
{
  "status": "ready | not ready",
  "checks": {
    "database": {
      "status": "ready | not ready",
      "error": null | "error message"
    },
    "stash": {
      "status": "ready | not ready",
      "error": null | "error message"
    },
    "openai": {
      "status": "ready | not ready | not configured",
      "error": null | "error message"
    }
  }
}
```

**Status Codes:**
- 200: All critical services ready
- 503: One or more critical services not ready

### GET /health/version
Get application version and build information.

**Response:**
```json
{
  "name": "StashHog",
  "version": "1.0.0",
  "environment": "production",
  "debug": false,
  "features": {
    "stash": true,
    "openai": true,
    "authentication": true
  }
}
```

### GET /health/ping
Simple ping endpoint for latency checks.

**Response:**
```json
{
  "timestamp": 1234567890.123
}
```

---

## Scene Endpoints
**Prefix:** `/scenes`

### GET /scenes/
List scenes with pagination and filters.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `per_page` (int, default: 50, max: 100): Items per page
- `sort_by` (string): Field to sort by
- `sort_order` (string, default: "asc"): Sort order ("asc" or "desc")
- `search` (string): Search in title and details
- `studio_id` (string): Filter by studio ID
- `performer_ids` (array[string]): Filter by performer IDs
- `tag_ids` (array[string]): Filter by tag IDs
- `organized` (boolean): Filter by organized status
- `date_from` (datetime): Filter by date from
- `date_to` (datetime): Filter by date to

**Response:**
```json
{
  "items": [
    {
      "id": "scene123",
      "title": "Scene Title",
      "paths": ["/path/to/file.mp4"],
      "organized": true,
      "details": "Scene description",
      "created_date": "2024-01-01T00:00:00",
      "scene_date": "2024-01-01T00:00:00",
      "studio": {
        "id": "studio123",
        "name": "Studio Name"
      },
      "performers": [
        {
          "id": "performer123",
          "name": "Performer Name"
        }
      ],
      "tags": [
        {
          "id": "tag123",
          "name": "Tag Name"
        }
      ],
      "last_synced": "2024-01-01T00:00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 50,
  "pages": 2
}
```

### GET /scenes/{scene_id}
Get a single scene by ID.

**Path Parameters:**
- `scene_id` (string): Scene ID

**Response:** Scene object (same as item in list response)

**Status Codes:**
- 200: Success
- 404: Scene not found

### POST /scenes/sync
Trigger scene synchronization from Stash.

**Query Parameters:**
- `background` (boolean, default: true): Run as background job
- `incremental` (boolean, default: true): Only sync new/updated scenes

**Response (background=true):**
```json
{
  "job_id": "job123",
  "status": "queued",
  "message": "Scene sync job has been queued"
}
```

**Response (background=false):**
```json
{
  "status": "completed",
  "scenes_processed": 100,
  "scenes_created": 10,
  "scenes_updated": 5,
  "errors": []
}
```

### POST /scenes/{scene_id}/resync
Resync a single scene from Stash.

**Path Parameters:**
- `scene_id` (string): Scene ID

**Response:** Updated scene object

**Status Codes:**
- 200: Success
- 404: Scene not found

### GET /scenes/stats/summary
Get scene statistics summary.

**Response:**
```json
{
  "total_scenes": 1000,
  "organized_scenes": 800,
  "organization_percentage": 80.0,
  "total_tags": 50,
  "total_performers": 100,
  "total_studios": 20,
  "scenes_by_studio": {
    "Studio A": 150,
    "Studio B": 120
  }
}
```

---

## Analysis Endpoints
**Prefix:** `/analysis`

### POST /analysis/generate
Generate analysis plan for scenes.

**Request Body:**
```json
{
  "scene_ids": ["scene1", "scene2"],  // OR use filters
  "filters": {
    "search": "keyword",
    "studio_id": "studio123",
    "organized": false
  },
  "options": {
    "detect_performers": true,
    "detect_studios": true,
    "detect_tags": true,
    "detect_details": true,
    "use_ai": true,
    "confidence_threshold": 0.7
  },
  "plan_name": "My Analysis Plan"
}
```

**Query Parameters:**
- `background` (boolean, default: true): Run as background job

**Response (background=true):**
```json
{
  "job_id": "job123",
  "status": "queued",
  "message": "Analysis job queued for 50 scenes"
}
```

**Response (background=false):**
```json
{
  "plan_id": 1,
  "status": "completed",
  "total_scenes": 50,
  "total_changes": 150
}
```

### GET /analysis/plans
List analysis plans.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `per_page` (int, default: 50): Items per page
- `status` (string): Filter by plan status

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Analysis Plan Name",
      "status": "pending | completed | applied",
      "created_at": "2024-01-01T00:00:00",
      "total_scenes": 50,
      "total_changes": 150,
      "metadata": {}
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 50,
  "pages": 1
}
```

### GET /analysis/plans/{plan_id}
Get plan with all changes.

**Path Parameters:**
- `plan_id` (int): Plan ID

**Response:**
```json
{
  "id": 1,
  "name": "Analysis Plan Name",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00",
  "total_scenes": 2,
  "total_changes": 5,
  "metadata": {},
  "scenes": [
    {
      "scene_id": "scene123",
      "scene_title": "Scene Title",
      "changes": [
        {
          "field": "tags",
          "action": "add",
          "current_value": ["tag1"],
          "proposed_value": ["tag1", "tag2"],
          "confidence": 0.95
        }
      ]
    }
  ]
}
```

### POST /analysis/plans/{plan_id}/apply
Apply plan changes.

**Path Parameters:**
- `plan_id` (int): Plan ID

**Query Parameters:**
- `scene_ids` (array[string]): Apply to specific scenes only
- `background` (boolean, default: true): Run as background job

**Response (background=true):**
```json
{
  "job_id": "job123",
  "status": "queued",
  "message": "Plan application job has been queued"
}
```

**Response (background=false):**
```json
{
  "status": "completed",
  "scenes_updated": 45,
  "changes_applied": 135,
  "errors": []
}
```

### PATCH /analysis/changes/{change_id}
Update individual change before applying.

**Path Parameters:**
- `change_id` (int): Change ID

**Request Body:**
```json
{
  "proposed_value": "new value"
}
```

**Response:**
```json
{
  "id": 1,
  "field": "tags",
  "action": "add",
  "current_value": ["tag1"],
  "proposed_value": "new value",
  "confidence": 0.95
}
```

---

## Job Endpoints
**Prefix:** `/jobs`

### GET /jobs/
List recent jobs.

**Query Parameters:**
- `status` (string): Filter by job status
- `job_type` (string): Filter by job type
- `limit` (int, default: 50, max: 100): Maximum number of jobs

**Response:**
```json
[
  {
    "id": "job123",
    "type": "scene_sync | scene_analysis | batch_analysis | sync_all | apply_plan",
    "status": "pending | running | completed | failed | cancelled",
    "progress": 75.5,
    "parameters": {},
    "result": {},
    "error": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T00:00:00"
  }
]
```

### GET /jobs/{job_id}
Get job details.

**Path Parameters:**
- `job_id` (string): Job ID

**Response:**
```json
{
  "id": "job123",
  "type": "scene_sync",
  "status": "running",
  "progress": 75.5,
  "parameters": {},
  "result": {},
  "error": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "completed_at": null,
  "logs": ["Log entry 1", "Log entry 2"],
  "metadata": {}
}
```

### DELETE /jobs/{job_id}
Cancel running job.

**Path Parameters:**
- `job_id` (string): Job ID

**Response:**
```json
{
  "success": true,
  "message": "Job job123 cancelled successfully"
}
```

**Status Codes:**
- 200: Success
- 400: Job cannot be cancelled (already completed/failed/cancelled)
- 404: Job not found

### WebSocket /jobs/{job_id}/ws
WebSocket for real-time job progress.

**Path Parameters:**
- `job_id` (string): Job ID

**WebSocket Messages:**

Client → Server:
```json
{
  "type": "ping"
}
```

Server → Client:
```json
{
  "type": "pong"
}
```

Server → Client (Job Status):
```json
{
  "type": "job_status",
  "job_id": "job123",
  "status": "running",
  "progress": 75.5,
  "message": "Processing scene 75 of 100",
  "result": null,
  "error": null
}
```

Server → Client (Error):
```json
{
  "type": "error",
  "message": "Job job123 not found"
}
```

---

## Settings Endpoints
**Prefix:** `/settings`

### GET /settings/
Get all application settings.

**Response:**
```json
[
  {
    "key": "app.name",
    "value": "StashHog",
    "description": "Application name"
  },
  {
    "key": "stash.api_key",
    "value": "********",
    "description": "Stash API key"
  }
]
```

Note: Sensitive values are masked with "********"

### GET /settings/{key}
Get a specific setting by key.

**Path Parameters:**
- `key` (string): Setting key

**Response:**
```json
{
  "key": "stash.url",
  "value": "http://localhost:9999",
  "description": "Stash URL"
}
```

### PUT /settings/{key}
Update a specific setting by key.

**Path Parameters:**
- `key` (string): Setting key

**Request Body:**
```json
{
  "value": "new value"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Setting 'stash.url' updated successfully",
  "key": "stash.url",
  "value": "new value"
}
```

### PUT /settings/
Update multiple application settings.

**Request Body:**
```json
{
  "stash_url": "http://localhost:9999",
  "stash_api_key": "new-api-key",
  "openai_api_key": "sk-...",
  "openai_model": "gpt-4",
  "analysis_confidence_threshold": 0.8,
  "sync_incremental": true,
  "sync_batch_size": 100
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "updated_fields": ["stash_url", "openai_api_key"],
  "requires_restart": true
}
```

### POST /settings/test-stash
Test Stash connection.

**Request Body (optional):**
```json
{
  "url": "http://localhost:9999",
  "api_key": "test-api-key"
}
```

**Response:**
```json
{
  "service": "stash",
  "success": true,
  "message": "Successfully connected to Stash server",
  "details": {
    "server_version": "0.20.0",
    "scene_count": 1000,
    "performer_count": 200
  }
}
```

### POST /settings/test-openai
Test OpenAI connection.

**Request Body (optional):**
```json
{
  "api_key": "sk-...",
  "model": "gpt-4"
}
```

**Response:**
```json
{
  "service": "openai",
  "success": true,
  "message": "Successfully connected to OpenAI API",
  "details": {
    "model": "gpt-4",
    "available_models": ["gpt-4", "gpt-3.5-turbo"],
    "total_models": 20
  }
}
```

---

## Sync Endpoints
**Prefix:** `/sync`

### POST /sync/all
Trigger full sync of all entities from Stash.

**Query Parameters:**
- `force` (boolean, default: false): Force full sync ignoring timestamps

**Response:**
```json
{
  "id": "job123",
  "type": "sync_all",
  "status": "pending",
  "progress": 0,
  "parameters": {
    "force": false
  },
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### POST /sync/scenes
Sync scenes from Stash.

**Request Body (optional):**
```json
{
  "scene_ids": ["scene1", "scene2"]
}
```

**Query Parameters:**
- `force` (boolean, default: false): Force sync even if unchanged

**Response:** Job response (same as /sync/all)

### POST /sync/performers
Sync performers from Stash.

**Query Parameters:**
- `force` (boolean, default: false): Force sync ignoring timestamps

**Response:** Job response

### POST /sync/tags
Sync tags from Stash.

**Query Parameters:**
- `force` (boolean, default: false): Force sync ignoring timestamps

**Response:** Job response

### POST /sync/studios
Sync studios from Stash.

**Query Parameters:**
- `force` (boolean, default: false): Force sync ignoring timestamps

**Response:** Job response

### POST /sync/scene/{scene_id}
Sync a single scene by ID (synchronous).

**Path Parameters:**
- `scene_id` (string): Scene ID to sync

**Response:**
```json
{
  "job_id": null,
  "status": "completed",
  "total_items": 1,
  "processed_items": 1,
  "created_items": 0,
  "updated_items": 1,
  "skipped_items": 0,
  "failed_items": 0,
  "started_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:00:05",
  "duration_seconds": 5.0,
  "errors": []
}
```

### GET /sync/stats
Get sync statistics.

**Response:**
```json
{
  "scene_count": 1000,
  "performer_count": 200,
  "tag_count": 50,
  "studio_count": 20,
  "last_scene_sync": "2024-01-01T00:00:00",
  "last_performer_sync": "2024-01-01T00:00:00",
  "last_tag_sync": "2024-01-01T00:00:00",
  "last_studio_sync": "2024-01-01T00:00:00",
  "pending_scenes": 0,
  "pending_performers": 0,
  "pending_tags": 0,
  "pending_studios": 0
}
```

---

## Entity Endpoints
**Prefix:** `/entities`

### GET /entities/performers
List all performers.

**Query Parameters:**
- `search` (string): Search performers by name

**Response:**
```json
[
  {
    "id": "performer123",
    "name": "Performer Name",
    "scene_count": 25
  }
]
```

### GET /entities/tags
List all tags.

**Query Parameters:**
- `search` (string): Search tags by name

**Response:**
```json
[
  {
    "id": "tag123",
    "name": "Tag Name",
    "scene_count": 100
  }
]
```

### GET /entities/studios
List all studios.

**Query Parameters:**
- `search` (string): Search studios by name

**Response:**
```json
[
  {
    "id": "studio123",
    "name": "Studio Name",
    "scene_count": 150
  }
]
```

---

## Common Response Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

## Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "error": "Brief error message",
  "detail": "Detailed error information",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Authentication

Currently, the API does not require authentication. However, the infrastructure supports JWT-based authentication which can be enabled in the security settings.

## Rate Limiting

No rate limiting is currently implemented, but the infrastructure supports it through middleware configuration.