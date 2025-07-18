# Greenlet Error Fix - Session Refresh After Job Creation [RESOLVED]

## Date: 2025-07-17
## Status: ✅ FIXED

## Error Details

### Error Message
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. 
Was IO attempted in an unexpected place? 
(Background on this error at: https://sqlalche.me/e/20/xd2s)
```

### Stack Trace Location
The error occurred in `/app/app/api/routes/sync.py` at line 66 when accessing `job.updated_at`:
```python
job_updated_at = job.updated_at
```

### Error Context
- Triggered when hitting the quick sync button to trigger an incremental sync job
- Error happens after `job_service.create_job()` returns a job object
- The job object appears to be detached from its SQLAlchemy session

## Root Cause Analysis

The issue is a classic SQLAlchemy lazy loading problem in an async context:

1. `job_service.create_job()` creates a job in its own database session
2. That session commits and closes after creating the job
3. The job object is returned but is now detached from any session
4. When the route handler tries to access `job.updated_at`, SQLAlchemy attempts to lazy load the attribute
5. This lazy load fails because there's no active async context (greenlet)

## Fix Attempted

### Solution: Refresh Job Object in Current Session

I added `await db.refresh(job)` after every `job_service.create_job()` call to reload the job object in the current session context.

### Files Modified

1. **backend/app/api/routes/sync.py**
   - Fixed 5 endpoints: `sync_all`, `sync_scenes`, `sync_performers`, `sync_tags`, `sync_studios`
   - Pattern fixed:
   ```python
   # Before
   job = await job_service.create_job(...)
   job_updated_at = job.updated_at  # This fails
   
   # After
   job = await job_service.create_job(...)
   await db.refresh(job)  # Reload in current session
   job_updated_at = job.updated_at  # Now safe
   ```

2. **backend/app/api/routes/scenes.py**
   - Fixed 2 job creation instances in sync endpoints
   
3. **backend/app/api/routes/analysis.py**
   - Fixed 2 job creation instances (analysis and apply_plan)
   
4. **backend/app/api/routes/jobs.py**
   - Fixed 1 instance in job retry endpoint
   
5. **backend/app/api/routes/schedules.py**
   - Fixed 1 instance in schedule trigger endpoint

### Why This Should Work

- `db.refresh(job)` reloads the job object from the database using the current session
- This ensures all attributes are loaded and accessible without triggering lazy loading
- The job object is now attached to the active session with proper async context

## Alternative Solutions (Not Implemented)

### Option 1: Eager Loading in job_service
Modify `job_service.create_job()` to eagerly load all attributes before returning:
```python
# In job_service.py
await db.refresh(job)
return job
```

### Option 2: Return Job ID Only
Change `job_service.create_job()` to return just the job ID, then fetch the job in the route:
```python
job_id = await job_service.create_job(...)
job = await job_repository.get_job(job_id, db)
```

### Option 3: Use joinedload/selectinload
Configure the Job model to eagerly load certain attributes by default.

## Testing Recommendations

1. Test the sync endpoint that was failing: `POST /api/sync/all`
2. Monitor logs for any greenlet errors
3. Test other job creation endpoints to ensure they work correctly
4. Check that job attributes (especially timestamps) are accessible

## If This Fix Doesn't Work

If the error persists after this fix, consider:

1. **Check Session Lifecycle**: The issue might be deeper in how sessions are managed between the job service and route handlers
2. **Investigate job_repository**: The job creation in the repository might have session management issues
3. **Review Async Context**: There might be a context switch happening that's not obvious
4. **Consider Option 2**: Return only the job ID from create_job and fetch it fresh in the route

## Fix Confirmation

✅ **This fix successfully resolved the greenlet error.** The `await db.refresh(job)` approach properly reattaches the job object to the current session context, allowing safe access to all attributes without triggering lazy loading issues.

## Prevention Guidelines

### 1. Always Refresh Objects Returned from Other Services

When a service method returns a SQLAlchemy model object that was created in a different session:

```python
# ✅ CORRECT: Refresh the object in your current session
job = await job_service.create_job(...)
await db.refresh(job)
# Now safe to access all attributes
job_id = job.id
job_updated_at = job.updated_at

# ❌ WRONG: Direct access may trigger lazy loading
job = await job_service.create_job(...)
job_updated_at = job.updated_at  # May fail with greenlet error
```

### 2. Design Service Methods Carefully

When designing service methods that return model objects:

**Option A: Return within same session (Preferred)**
```python
async def create_something(db: AsyncSession, ...):
    item = await repository.create(db, ...)
    # Don't close/commit the session here
    return item
```

**Option B: Return only IDs**
```python
async def create_something(...) -> str:
    async with AsyncSessionLocal() as db:
        item = await repository.create(db, ...)
        item_id = item.id
        await db.commit()
    return item_id  # Return primitive, not model object
```

**Option C: Eagerly load before returning**
```python
async def create_something(...):
    async with AsyncSessionLocal() as db:
        item = await repository.create(db, ...)
        await db.commit()
        await db.refresh(item)  # Ensure fully loaded
    return item
```

### 3. Watch for These Patterns

Be extra careful when you see:
- Service methods that create their own sessions (`async with AsyncSessionLocal()`)
- Methods that return SQLAlchemy model objects
- Accessing model attributes after service method calls
- Cross-service communication involving model objects

### 4. Best Practices Checklist

- [ ] **Refresh Pattern**: Always refresh objects returned from services that use different sessions
- [ ] **Explicit Loading**: Access all needed attributes while the session is active
- [ ] **Session Scope**: Keep database operations within clear session boundaries
- [ ] **Primitive Returns**: Consider returning IDs/dicts instead of model objects from services
- [ ] **Documentation**: Document when methods return detached objects

### 5. Code Review Points

When reviewing code, look for:
```python
# Red flags:
result = await some_service.create_something(...)
value = result.some_attribute  # Potential greenlet error

# Safe patterns:
result = await some_service.create_something(...)
await db.refresh(result)  # Or ensure service returns attached object
value = result.some_attribute  # Safe
```

## Testing for Greenlet Issues

1. **Unit Tests**: Mock services to return detached objects and verify refresh is called
2. **Integration Tests**: Test full request flow with real database sessions
3. **Load Tests**: Greenlet errors often appear under concurrent load

## Summary

The greenlet error was caused by accessing attributes on a SQLAlchemy model object that was detached from its session. The fix (`await db.refresh(job)`) successfully resolved this by reattaching the object to the current session. To prevent future occurrences, always refresh objects returned from services that manage their own database sessions, or redesign services to return primitive values instead of model objects.

## Related Documentation

- Original greenlet error resolution guide: `/plans/greenlet_error.md`
- SQLAlchemy async documentation: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Greenlet context error explanation: https://sqlalche.me/e/20/xd2s