# Fix Plan for MyPy Type Errors

## Overview

This plan outlines the steps needed to fix MyPy type errors in the sync module while maintaining the greenlet error fixes. The main issue is that we have a mix of sync and async database operations, and some code is still using the old SQLAlchemy query API which doesn't exist on AsyncSession.

## Background: Greenlet Error Fix

The greenlet error was fixed by:
1. Using `AsyncSessionLocal` instead of `SessionLocal` in all job handlers
2. Using `async with AsyncSessionLocal()` context managers
3. Making all database operations async (using `await` on execute, commit, rollback)

**IMPORTANT**: Do NOT revert back to using `SessionLocal` or sync database operations in job handlers, as this will reintroduce the greenlet error.

## Current State

- `SyncService` accepts `AsyncSession` in its constructor
- Handler classes (`EntitySyncHandler`, `SceneSyncHandler`) accept `Union[Session, AsyncSession]`
- Some methods still use the old `.query()` API which only exists on sync `Session`
- The scheduler is using `AsyncSessionLocal` but has missing `await` keywords

## Issues to Fix

### 1. Old Query API Usage (13 errors)

**Files affected:**
- `app/services/sync/scene_sync.py` (lines 40, 105, 222, 252, 281, 303)
- `app/services/sync/entity_sync.py` (lines 142, 164, 260, 263, 275, 279)

**Problem:** Code like `db.query(Model).filter(...).first()` doesn't work with AsyncSession

**Solution:** Convert to modern SQLAlchemy 2.0 style:
```python
# Old style (doesn't work with AsyncSession)
existing = db.query(Scene).filter(Scene.id == scene_id).first()

# New style (works with both Session and AsyncSession)
from sqlalchemy import select
stmt = select(Scene).where(Scene.id == scene_id)
if isinstance(db, AsyncSession):
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
else:
    result = db.execute(stmt)
    existing = result.scalar_one_or_none()
```

### 2. SceneSyncerWrapper Type Issues (2 errors)

**Files affected:**
- `app/services/sync/sync_service.py` (lines 306, 320)

**Problem:** SceneSyncerWrapper expects sync `Session` but receives `AsyncSession`

**Solution:** Update SceneSyncerWrapper methods to accept `Union[Session, AsyncSession]`

### 3. Missing Await Keywords (4 errors)

**Files affected:**
- `app/services/sync/scheduler.py` (lines 172, 193, 221, 255)

**Problem:** Async operations not being awaited

**Solution:** Add `await` keyword before `db.commit()` calls

### 4. Scheduler Type Mismatches (4 errors)

**Files affected:**
- `app/services/sync/scheduler.py` (lines 196, 200, 258, 262)

**Problem:** `_update_scheduled_task` expects sync `Session` but receives `AsyncSession`

**Solution:** Update method signature to accept `Union[Session, AsyncSession]`

## Implementation Steps

### Step 1: Create Helper Function for Database Operations

Create a utility function to handle both sync and async sessions:

```python
# In app/services/sync/utils.py
from typing import Union, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

async def get_by_id(
    db: Union[Session, AsyncSession],
    model: Type[T],
    id: str
) -> Optional[T]:
    """Get a model instance by ID, handling both sync and async sessions."""
    stmt = select(model).where(model.id == id)
    
    if isinstance(db, AsyncSession):
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    else:
        result = db.execute(stmt)
        return result.scalar_one_or_none()
```

### Step 2: Update scene_sync.py

1. Import the helper function or implement inline checks
2. Replace all `.query()` usage with modern SQLAlchemy style
3. Add proper type checking for AsyncSession vs Session

Example for line 40:
```python
# Old
existing_scene = db.query(Scene).filter(Scene.id == scene_id).first()

# New
stmt = select(Scene).where(Scene.id == scene_id)
if isinstance(db, AsyncSession):
    result = await db.execute(stmt)
    existing_scene = result.scalar_one_or_none()
else:
    result = db.execute(stmt)
    existing_scene = result.scalar_one_or_none()
```

### Step 3: Update entity_sync.py

Apply the same pattern as Step 2 for all `.query()` usage in entity_sync.py

### Step 4: Update SceneSyncerWrapper

In `sync_service.py`, update the SceneSyncerWrapper class definition:
```python
async def sync_scenes_with_filters(
    self, db: Union[Session, AsyncSession], filters: Dict[str, Any], progress_callback: Any = None
) -> SyncResult:
    # Implementation
```

### Step 5: Fix Scheduler

1. Add missing `await` keywords:
```python
# Line 172, 193, 221, 255
await db.commit()
```

2. Update `_update_scheduled_task` signature:
```python
def _update_scheduled_task(
    self, db: Union[Session, AsyncSession], task_name: str, last_run: datetime
) -> None:
```

## Testing

After implementing fixes:

1. Run MyPy to ensure all type errors are resolved:
   ```bash
   mypy app/ --ignore-missing-imports
   ```

2. Run the sync tests to ensure functionality isn't broken:
   ```bash
   pytest tests/test_sync_service_working.py -v
   ```

3. Test a real sync operation to ensure no greenlet errors occur

## Important Notes

1. **DO NOT** change `AsyncSessionLocal` back to `SessionLocal` in job handlers
2. **DO NOT** remove `async with` context managers in job handlers
3. **DO NOT** remove `await` from database operations in SyncService methods
4. When adding type checks for `isinstance(db, AsyncSession)`, remember to handle both cases

## Alternative Approach

If the mixed session types become too complex, consider:
1. Making everything consistently use AsyncSession
2. Creating separate sync and async versions of the handlers
3. Using a database session adapter pattern

However, the mixed approach should work fine with proper type checking.