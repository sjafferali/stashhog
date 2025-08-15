# Centralized Services

This document describes the centralized services that provide single sources of truth for common operations across the StashHog application. These services eliminate code duplication and ensure consistent behavior across all components.

## Overview

The centralized services pattern ensures that critical business logic exists in exactly one place, making the codebase easier to maintain, test, and reason about. All components that need to perform these operations use these centralized services rather than implementing their own versions.

## Services

### 1. SyncStatusService

**Location:** `backend/app/services/sync_status_service.py`

**Purpose:** Provides a single source of truth for checking sync status and determining which scenes need to be synced from Stash.

**Key Methods:**

- `get_pending_scenes_count(db, last_sync=None)` - Returns the count of scenes that have been updated in Stash since the last sync
- `get_last_sync_time(db, entity_type)` - Returns the last successful sync time for a given entity type (scene, performer, tag, studio)
- `get_sync_status(db)` - Returns comprehensive sync status information including last sync times and pending counts

**Used By:**
- `DashboardStatusService` - For displaying sync status on the dashboard
- `AutoStashSyncDaemon` - For checking if an incremental sync is needed
- Frontend sync pages - For displaying sync information to users

**When to Use:**
- When you need to determine how many scenes are pending sync from Stash
- When you need to get the last sync time for any entity type
- When you need comprehensive sync status information

**Example Usage:**
```python
from app.services.sync_status_service import SyncStatusService
from app.services.stash_service import StashService

stash_service = StashService(url, api_key)
sync_status_service = SyncStatusService(stash_service)

async with AsyncSessionLocal() as db:
    # Get pending scenes count
    pending_count = await sync_status_service.get_pending_scenes_count(db)
    
    # Get last sync time for scenes
    last_sync = await sync_status_service.get_last_sync_time(db, "scene")
    
    # Get full sync status
    status = await sync_status_service.get_sync_status(db)
```

### 2. DownloadCheckService

**Location:** `backend/app/services/download_check_service.py`

**Purpose:** Provides a single source of truth for managing and checking downloads from qBittorrent that need processing.

**Key Methods:**

- `connect_to_qbittorrent()` - Establishes and authenticates connection to qBittorrent
- `get_pending_downloads()` - Returns list of torrents that need to be processed (completed torrents without 'synced' or 'error_syncing' tags)
- `get_pending_downloads_count()` - Returns count of pending downloads
- `_filter_pending_torrents(torrents)` - Filters torrents to only include those pending processing

**Used By:**
- `DashboardStatusService` - For displaying pending downloads count
- `DownloadProcessorDaemon` - For checking if downloads need processing
- `process_downloads_job` - For getting torrents to process
- `process_new_scenes_job` - For workflow orchestration

**When to Use:**
- When you need to check how many downloads are pending processing
- When you need to get the actual list of torrents to process
- When you need to connect to qBittorrent (use the centralized connection method)

**Example Usage:**
```python
from app.services.download_check_service import download_check_service

# Get count of pending downloads (for dashboard display)
pending_count = await download_check_service.get_pending_downloads_count()

# Get actual torrents to process (for jobs)
torrents = await download_check_service.get_pending_downloads()
for torrent in torrents:
    # Process each torrent
    process_torrent(torrent)
```

**Singleton Instance:** The service is available as a singleton instance `download_check_service` that should be imported and used directly.

### 3. Job Registry

**Location:** `backend/app/core/job_registry.py`

**Purpose:** Provides a single source of truth for all job type definitions, metadata, and configuration. This eliminates the need to update multiple locations when adding new job types or changing job labels.

**Key Components:**

- `JOB_REGISTRY` - Central dictionary containing all job type metadata
- `JobMetadata` dataclass - Defines structure for job metadata including labels, descriptions, colors, categories, and execution properties
- API endpoint at `/jobs/metadata` - Exposes registry to frontend

**Frontend Access:** `frontend/src/services/jobMetadataService.ts`
- Fetches and caches job metadata from backend
- Provides convenient methods for accessing job labels, colors, descriptions, and units
- Falls back to local definitions if backend is unavailable

**Key Functions:**

Backend:
- `get_job_metadata(job_type)` - Get metadata for a specific job type
- `to_api_response()` - Convert registry to API response format
- `get_job_type_mapping()` - Get mapping from model to schema job types
- `validate_job_type(job_type)` - Check if a job type is registered

Frontend:
- `jobMetadataService.fetchMetadata()` - Fetch metadata from backend (cached)
- `jobMetadataService.getJobLabel(type)` - Get display label for job type
- `jobMetadataService.getJobColor(type)` - Get color for job type
- `jobMetadataService.getJobDescription(type)` - Get description for job type
- `jobMetadataService.formatJobProgress(...)` - Format progress with appropriate units

**Used By:**
- All frontend components displaying job information (Dashboard, Jobs page, Job Monitor, etc.)
- Backend job service for validation and metadata
- API routes for job type information

**When to Use:**
- When displaying job type names anywhere in the UI
- When adding a new job type (only need to add it to the registry)
- When needing job metadata like descriptions, colors, or categories
- When formatting job progress with appropriate units

**Example Usage:**

Backend:
```python
from app.core.job_registry import get_job_metadata, validate_job_type

# Validate a job type
if validate_job_type("sync_scenes"):
    metadata = get_job_metadata("sync_scenes")
    print(f"Job label: {metadata.label}")
    print(f"Job color: {metadata.color}")
```

Frontend:
```typescript
import { jobMetadataService } from '@/services/jobMetadataService';

// Fetch metadata on app initialization
await jobMetadataService.fetchMetadata();

// Get job label for display
const label = jobMetadataService.getJobLabel('sync_scenes');  // Returns "Sync Scenes"

// Format job progress
const progress = jobMetadataService.formatJobProgress(
  'sync_scenes', 
  50,  // processed
  100, // total
  50   // percentage
);  // Returns "50 / 100 scenes"
```

**Adding a New Job Type:**

To add a new job type, you only need to update the `JOB_REGISTRY` in `backend/app/core/job_registry.py`:

```python
"MY_NEW_JOB": JobMetadata(
    value="my_new_job",
    label="My New Job",
    description="Description of what this job does",
    color="blue",
    category="My Category",
    unit="items",
    allow_concurrent=True,
)
```

The new job type will automatically be available throughout the application with consistent labeling.

## Benefits of Centralization

1. **Single Source of Truth**: Each piece of logic exists in exactly one place
2. **Consistency**: All components behave identically when performing the same operation
3. **Maintainability**: Changes to business logic only need to be made in one place
4. **Testability**: Services can be unit tested independently
5. **Reduced Bugs**: Eliminates bugs caused by inconsistent implementations
6. **Performance**: Allows for caching and optimization at the service level

## Migration Guide

If you find code that duplicates the functionality of these centralized services, you should:

1. Import the appropriate centralized service
2. Replace the duplicate logic with a call to the service method
3. Remove the duplicate code
4. Test to ensure the behavior remains consistent

## Best Practices

1. **Always use the centralized services** when their functionality is needed
2. **Never duplicate** the logic from these services elsewhere in the codebase
3. **Add to existing services** rather than creating new duplicate functionality
4. **Keep services focused** - each service should have a single, clear purpose
5. **Document service methods** thoroughly to make their purpose clear
6. **Use dependency injection** where possible to make testing easier

## Adding New Centralized Services

When you identify logic that is duplicated across multiple components:

1. Create a new service class in `backend/app/services/`
2. Move the common logic to the service
3. Update all existing code to use the new service
4. Add comprehensive tests for the service
5. Document the service in this file

## Related Documentation

- [Dashboard Status Checks](./dashboard-status-checks.md) - Uses centralized services
- [Jobs](./adding-new-jobs.md) - Jobs should use centralized services
- [Daemons](./adding-new-daemons.md) - Daemons should use centralized services