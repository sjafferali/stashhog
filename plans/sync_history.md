# Sync History Implementation Plan

## Overview
This document outlines the implementation plan for adding sync history tracking to individual scenes. The goal is to create a new `sync_log` table that tracks which scenes were included in sync operations and display this information in the scene details History tab.

## Problem Statement
Currently, the `sync_history` table only tracks aggregate sync operations without recording which specific scenes were synced. This makes it impossible to show sync history for individual scenes without guessing based on timestamps.

## Solution
Create a new `sync_log` table to track individual entity sync operations with the following approach:
- One row per scene for incremental and scene-specific syncs
- One row with NULL entity_id for full syncs (affects all scenes)
- Track whether each sync resulted in changes
- Display this information in the scene's History tab

## Database Design

### New Table: `sync_log`
```sql
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_history_id INTEGER NOT NULL,  -- FK to sync_history table
    entity_type VARCHAR NOT NULL,      -- 'scene', 'performer', 'tag', 'studio'
    entity_id VARCHAR,                 -- Scene ID (NULL for full syncs)
    sync_type VARCHAR NOT NULL,        -- 'full', 'incremental', 'specific'
    had_changes BOOLEAN DEFAULT FALSE, -- Whether the entity was modified
    change_type VARCHAR,               -- 'created', 'updated', 'skipped', 'failed'
    error_message TEXT,                -- Error details if failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sync_history_id) REFERENCES sync_history(id),
    INDEX idx_entity_id (entity_id),
    INDEX idx_sync_history_id (sync_history_id)
);
```

## Implementation Steps

### 1. Database Migration
**File:** `backend/alembic/versions/XXX_add_sync_log_table.py`

Create a new Alembic migration to:
- Create the `sync_log` table
- Add appropriate indexes for query performance
- Set up foreign key relationship to `sync_history`

### 2. Model Definition
**File:** `backend/app/models/sync_log.py`

```python
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

class SyncLog(BaseModel):
    __tablename__ = "sync_log"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_history_id = Column(Integer, ForeignKey('sync_history.id'), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, index=True)
    sync_type = Column(String, nullable=False)  # 'full', 'incremental', 'specific'
    had_changes = Column(Boolean, default=False)
    change_type = Column(String)  # 'created', 'updated', 'skipped', 'failed'
    error_message = Column(Text)
    
    # Relationship
    sync_history = relationship("SyncHistory", backref="sync_logs")
```

### 3. Update Sync Service
**File:** `backend/app/services/sync/sync_service.py`

Add methods to create sync log entries during sync operations:

```python
async def _create_sync_log(
    self,
    sync_history_id: int,
    entity_type: str,
    entity_id: Optional[str],
    sync_type: str,
    had_changes: bool = False,
    change_type: Optional[str] = None,
    error_message: Optional[str] = None
):
    """Create a sync log entry for tracking individual entity syncs."""
    from app.models.sync_log import SyncLog
    
    sync_log = SyncLog(
        sync_history_id=sync_history_id,
        entity_type=entity_type,
        entity_id=entity_id,
        sync_type=sync_type,
        had_changes=had_changes,
        change_type=change_type,
        error_message=error_message
    )
    self.db.add(sync_log)
    # Note: Don't commit here, let the parent transaction handle it
```

Update sync methods to create log entries:

#### For Full Sync (`sync_all`):
- Create a sync_log entry with entity_id=NULL at the start
- Update the entry based on overall results

#### For Scene-Specific Sync (`sync_scenes`):
- Create individual sync_log entries for each scene
- Track the outcome for each scene (created/updated/skipped/failed)

#### For Incremental Sync:
- Similar to scene-specific sync, but marked as 'incremental' type

### 4. Update Scene Sync Handler
**File:** `backend/app/services/sync/scene_sync.py`

Modify the sync methods to track individual scene outcomes:

```python
async def sync_scene(self, scene_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Sync a single scene and track the outcome."""
    scene_id = scene_data.get('id')
    result = {
        'had_changes': False,
        'change_type': 'skipped',
        'error': None
    }
    
    try:
        # Existing sync logic...
        
        if created:
            result['had_changes'] = True
            result['change_type'] = 'created'
        elif updated:
            result['had_changes'] = True
            result['change_type'] = 'updated'
        else:
            result['change_type'] = 'skipped'
            
    except Exception as e:
        result['change_type'] = 'failed'
        result['error'] = str(e)
        
    return result
```

### 5. API Endpoint
**File:** `backend/app/api/routes/scenes.py`

Add a new endpoint to fetch sync logs for a specific scene:

```python
@router.get("/{scene_id}/sync-logs", response_model=List[SyncLogResponse])
async def get_scene_sync_logs(
    scene_id: str,
    limit: int = Query(50, description="Maximum number of logs to return"),
    db: AsyncSession = Depends(get_db)
) -> List[SyncLogResponse]:
    """
    Get sync history logs for a specific scene.
    
    Returns sync logs where:
    - The scene was specifically synced (entity_id matches)
    - A full sync was performed (entity_id is NULL)
    """
    from sqlalchemy import or_, and_
    from app.models.sync_log import SyncLog
    from app.models.sync_history import SyncHistory
    
    query = (
        select(SyncLog, SyncHistory)
        .join(SyncHistory, SyncLog.sync_history_id == SyncHistory.id)
        .where(
            or_(
                SyncLog.entity_id == scene_id,
                and_(
                    SyncLog.entity_id.is_(None),
                    SyncLog.sync_type == 'full'
                )
            )
        )
        .order_by(SyncLog.created_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    sync_logs = result.all()
    
    return [
        {
            "id": log.SyncLog.id,
            "sync_type": log.SyncLog.sync_type,
            "had_changes": log.SyncLog.had_changes,
            "change_type": log.SyncLog.change_type,
            "error_message": log.SyncLog.error_message,
            "created_at": log.SyncLog.created_at,
            "sync_history": {
                "job_id": log.SyncHistory.job_id,
                "started_at": log.SyncHistory.started_at,
                "completed_at": log.SyncHistory.completed_at,
                "status": log.SyncHistory.status,
                "items_synced": log.SyncHistory.items_synced,
                "items_created": log.SyncHistory.items_created,
                "items_updated": log.SyncHistory.items_updated,
            }
        }
        for log in sync_logs
    ]
```

### 6. Frontend Integration
**File:** `frontend/src/pages/scenes/components/SceneDetailModal.tsx`

Add a query to fetch sync logs:

```typescript
// Add to the component
const { data: syncLogs } = useQuery<SyncLogEntry[]>(
  ['scene-sync-logs', scene.id],
  async () => {
    const response = await api.get(`/scenes/${scene.id}/sync-logs`);
    return response.data;
  },
  {
    enabled: visible && activeTab === 'history',
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  }
);
```

Update the `renderHistoryTab` function to include sync logs:

```typescript
const renderHistoryTab = () => {
  // Combine all history items and sort by date
  const historyItems = [];
  
  // Add scene creation
  if (fullScene?.stash_created_at) {
    historyItems.push({
      type: 'created',
      date: fullScene.stash_created_at,
      color: 'green',
      title: 'Scene Created in Stash',
    });
  }
  
  // Add sync logs
  syncLogs?.forEach(log => {
    const syncTypeLabel = {
      'full': 'Full Sync (All Scenes)',
      'incremental': 'Incremental Sync',
      'specific': 'Scene Sync'
    }[log.sync_type] || log.sync_type;
    
    const color = log.change_type === 'failed' ? 'red' : 
                  log.had_changes ? 'blue' : 'gray';
    
    historyItems.push({
      type: 'sync',
      date: log.created_at,
      color,
      title: syncTypeLabel,
      subtitle: log.change_type ? `Status: ${log.change_type}` : undefined,
      error: log.error_message,
      jobId: log.sync_history.job_id,
    });
  });
  
  // Add analysis results
  analysisResults?.forEach((result, index) => {
    historyItems.push({
      type: 'analysis',
      date: result.created_at,
      color: 'purple',
      title: `Analysis #${index + 1}`,
      subtitle: `Plan: ${result.plan?.name || 'Unknown'}`,
    });
  });
  
  // Sort by date descending
  historyItems.sort((a, b) => 
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
  
  // Render timeline
  return (
    <Timeline>
      {historyItems.map((item, index) => (
        <Timeline.Item key={`${item.type}-${index}`} color={item.color}>
          <Text strong>{item.title}</Text>
          {item.subtitle && (
            <>
              <br />
              <Text type="secondary">{item.subtitle}</Text>
            </>
          )}
          {item.error && (
            <>
              <br />
              <Text type="danger">Error: {item.error}</Text>
            </>
          )}
          <br />
          <Text type="secondary">
            {dayjs(item.date).format('YYYY-MM-DD HH:mm:ss')}
          </Text>
        </Timeline.Item>
      ))}
    </Timeline>
  );
};
```

### 7. Type Definitions
**File:** `frontend/src/types/models.ts`

Add TypeScript interfaces:

```typescript
export interface SyncLogEntry {
  id: number;
  sync_type: 'full' | 'incremental' | 'specific';
  had_changes: boolean;
  change_type: 'created' | 'updated' | 'skipped' | 'failed' | null;
  error_message: string | null;
  created_at: string;
  sync_history: {
    job_id: string;
    started_at: string;
    completed_at: string | null;
    status: string;
    items_synced: number;
    items_created: number;
    items_updated: number;
  };
}
```

## Benefits

1. **Accurate Tracking**: Know exactly which scenes were included in each sync operation
2. **Change Detection**: See whether a sync actually modified the scene or left it unchanged
3. **Error Visibility**: Track sync failures at the individual scene level
4. **Full Sync Awareness**: Show when full syncs affected all scenes
5. **Audit Trail**: Complete history of all sync operations affecting a scene
6. **Performance**: Indexed queries for fast retrieval of scene-specific sync history

## Future Enhancements

1. **Filtering Options**: Add UI filters to show only syncs with changes, errors, etc.
2. **Pagination**: Add pagination if scenes accumulate many sync logs
3. **Data Retention**: Implement a cleanup job to remove old sync logs after a configurable period
4. **Bulk Operations**: Track which scenes were part of bulk resync operations
5. **Statistics**: Show sync success rates and patterns over time
6. **Notifications**: Alert users when sync errors occur for specific scenes

## Migration Strategy

1. The new sync_log table will start empty
2. Historical sync data won't be backfilled (not possible without scene-level data)
3. New syncs will immediately start populating the sync_log table
4. The History tab will show sync logs as they accumulate going forward

## Performance Considerations

1. **Indexes**: Entity_id index ensures fast lookups for scene-specific logs
2. **Batch Inserts**: Use bulk inserts when logging multiple scenes in a sync
3. **Query Limits**: Default to showing last 50 sync logs per scene
4. **Caching**: Frontend caches sync log queries for 5 minutes