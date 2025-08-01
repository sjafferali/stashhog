# Dashboard Status Checks

The dashboard displays real-time status information and actionable items by performing various checks when loaded. This document explains the current status checks and provides guidelines for adding new ones.

## Overview

All dashboard status checks are centralized in the `DashboardStatusService` class (`backend/app/services/dashboard_status_service.py`). This service consolidates all on-demand checks into a single location, making it easier to maintain and extend.

## Current Status Checks

### 1. Pending Scenes Check
- **Purpose**: Identifies scenes that have been updated in Stash since the last sync
- **How it works**: 
  - Queries the database for the last successful scene sync timestamp
  - Calls Stash API to count scenes updated after that timestamp
  - Handles timezone conversions for accurate comparison
- **Actionable Item**: Shows "Run Incremental Sync" button when pending scenes exist

### 2. Downloads Needing Processing
- **Purpose**: Checks for completed torrents that need to be processed
- **How it works**:
  - Connects to qBittorrent API
  - Queries for completed torrents with category "xxx" 
  - Filters out torrents that already have the "synced" tag
- **Actionable Item**: Shows "Process Downloads" button when unprocessed downloads exist

### 3. Analysis Status
- **Checks performed**:
  - Count of scenes not analyzed
  - Count of scenes not video analyzed
  - Draft analysis plans count
  - Analysis plans under review
  - Whether analysis jobs are running
- **Actionable Items**: Various buttons to view/review analysis tasks

### 4. Organization Status
- **Purpose**: Tracks scenes that need organization
- **Checks**: Count of unorganized scenes

### 5. Metadata Quality
- **Checks performed**:
  - Scenes without files
  - Scenes missing details
  - Scenes without studio assignment
  - Scenes without performers
  - Scenes without tags
- **Actionable Items**: Links to view scenes with missing metadata

### 6. Job Status
- **Purpose**: Monitors background job activity
- **Checks**:
  - Currently running jobs
  - Recently completed jobs
  - Failed jobs in the last 24 hours

## Architecture

### Backend Components

1. **DashboardStatusService** (`backend/app/services/dashboard_status_service.py`)
   - Central service that performs all status checks
   - Returns consolidated status data in a single call
   - Generates actionable items based on status data

2. **API Endpoint** (`backend/app/api/routes/sync.py`)
   - `/sync/stats` endpoint returns dashboard status data
   - Simply instantiates `DashboardStatusService` and calls `get_all_status_data()`

3. **Supporting Services**
   - `DownloadCheckService`: Handles qBittorrent connection and download checks
   - `StashService`: Handles Stash API calls for pending scenes

### Frontend Components

1. **Dashboard Component** (`frontend/src/pages/Dashboard.tsx`)
   - Fetches status data on mount
   - Displays actionable items as cards
   - Handles actions (sync, process downloads, navigation)
   - Auto-refreshes when jobs are running
   - Manual refresh button available

2. **API Client** (`frontend/src/services/apiClient.ts`)
   - `getSyncStatus()`: Fetches dashboard status data
   - `processDownloads()`: Starts download processing job

## Adding New Status Checks

To add a new status check to the dashboard:

### 1. Backend Changes

#### Update the Status Service
In `backend/app/services/dashboard_status_service.py`:

```python
# Add a new method for your check
async def _get_my_new_status(self, db: AsyncDBSession) -> Dict[str, Any]:
    """Get status for my new feature."""
    # Perform your checks here
    count = await db.execute(select(func.count(MyModel.id)).where(...))
    items_needing_action = count.scalar_one()
    
    return {
        "items_needing_action": items_needing_action,
        # Add other relevant metrics
    }

# Update get_all_status_data() to include your check
async def get_all_status_data(self, db: AsyncDBSession) -> Dict[str, Any]:
    # ... existing code ...
    my_new_status = await self._get_my_new_status(db)
    
    # Add to actionable items if needed
    actionable_items = self._generate_actionable_items(
        # ... existing parameters ...
        my_new_status=my_new_status,
    )
    
    return {
        # ... existing returns ...
        "my_feature": my_new_status,
    }

# Update _generate_actionable_items() if you have actionable items
def _generate_actionable_items(self, ..., my_new_status: Dict[str, Any]) -> List[Dict[str, Any]]:
    # ... existing code ...
    
    items_needing_action = my_new_status.get("items_needing_action", 0)
    if items_needing_action > 0:
        items.append({
            "id": "my_action_id",
            "type": "sync",  # or "analysis", "organization", "system"
            "title": "My Action Title",
            "description": f"{items_needing_action} items need attention",
            "count": items_needing_action,
            "action": "my_action",  # or "route" for navigation
            "action_label": "Process Items",
            "route": "/my-route",  # if navigating instead of action
            "priority": "high",  # "high", "medium", or "low"
            "visible": True,
        })
```

#### Create Supporting Services if Needed
If your check requires external API calls or complex logic:

```python
# backend/app/services/my_check_service.py
class MyCheckService:
    async def check_status(self) -> int:
        # Perform your check
        return count

my_check_service = MyCheckService()
```

### 2. Frontend Changes

#### Update Type Definitions
In `frontend/src/types/models.ts`:

```typescript
export interface SyncStatus {
  // ... existing fields ...
  my_feature?: {
    items_needing_action: number;
    // Other fields
  };
}
```

#### Handle New Actions
In `frontend/src/pages/Dashboard.tsx`:

```typescript
// Add loading state if needed
const [processingMyAction, setProcessingMyAction] = useState(false);

// Update handleAction()
const handleAction = async (item: ActionableItem) => {
  // ... existing cases ...
  
  case 'my_action':
    setProcessingMyAction(true);
    try {
      await apiClient.myActionMethod();
      await fetchStats(); // Refresh after action
    } catch (error) {
      console.error('Failed to process my action:', error);
    } finally {
      setProcessingMyAction(false);
    }
    break;
};

// Update loading state in button
loading={
  // ... existing conditions ...
  (item.action === 'my_action' && processingMyAction)
}
```

#### Add API Methods if Needed
In `frontend/src/services/apiClient.ts`:

```typescript
async myActionMethod(): Promise<Job> {
  const response = await api.post('/my-endpoint');
  return response.data;
}
```

## Best Practices

1. **Performance**: Keep checks lightweight - they run on every dashboard load
2. **Error Handling**: Use try-catch blocks and return sensible defaults on failure
3. **Caching**: Consider caching expensive checks if appropriate
4. **Consistency**: Follow the existing pattern for actionable items
5. **Priority Levels**:
   - `high`: Urgent items that block normal operation
   - `medium`: Important but not urgent
   - `low`: Nice to have, informational

## Manual Refresh

The dashboard includes a manual refresh button that:
- Calls all status checks again
- Updates all displayed metrics
- Shows loading state during refresh
- Useful when users want immediate updates

## Auto-Refresh

The dashboard automatically refreshes every 3 seconds when there are running jobs, ensuring users see real-time progress.

## Testing

When adding new checks:
1. Test with various data states (empty, partial, full)
2. Verify error handling when external services are unavailable
3. Check performance impact on dashboard load time
4. Ensure actionable items appear/disappear correctly
5. Test the action handlers thoroughly