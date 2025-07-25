# Greenlet Async Context Error: Resolution Guide

## Overview

The greenlet error (`greenlet_spawn has not been called; can't call await_only() here`) is a common issue when working with SQLAlchemy's async sessions in background jobs. This document explains the root cause, the fix implemented, and guidelines for preventing this error in future job implementations.

## The Error

```
greenlet_spawn has not been called; can't call await_only() here. 
Was IO attempted in an unexpected place? 
(Background on this error at: https://sqlalche.me/e/20/xd2s)
```

## Root Cause

This error occurs when SQLAlchemy async operations are performed outside of a proper async context. The most common scenarios are:

1. **Cross-Session Operations**: When a database operation tries to use a session that was created in a different async context
2. **Session Lifecycle Issues**: When database operations occur after a session has been closed
3. **Mixed Sync/Async Operations**: When synchronous code tries to interact with async sessions

In our case, the issue was in the job service's progress callback mechanism. The job handler would close its database session, then the job service would try to update the job status using a new session, causing a context mismatch.

## The Fix

The fix involved ensuring that each database operation happens within its own properly scoped async context:

### Before (Problematic Code)

```python
async def task_wrapper() -> str:
    try:
        # This creates a cross-context issue
        await self._update_job_status(
            job_id=job_id, status=JobStatus.RUNNING, message="Job started"
        )
        
        # Handler executes with its own db session
        result = await handler(job_id=job_id, **kwargs)
        
        # This tries to create a new session after handler's session closed
        await self._update_job_status(
            job_id=job_id, status=JobStatus.COMPLETED
        )
```

### After (Fixed Code)

```python
async def task_wrapper() -> str:
    from app.core.database import AsyncSessionLocal
    
    try:
        # Create a dedicated session for status updates
        async with AsyncSessionLocal() as status_db:
            await self._update_job_status_with_session(
                job_id=job_id, 
                status=JobStatus.RUNNING, 
                message="Job started",
                db=status_db
            )
            await status_db.commit()
        
        # Progress callback with its own session
        async def async_progress_callback(progress: int, message: Optional[str] = None) -> None:
            async with AsyncSessionLocal() as progress_db:
                await self._update_job_status_with_session(
                    job_id=job_id,
                    status=JobStatus.RUNNING,
                    progress=progress,
                    message=message,
                    db=progress_db
                )
                await progress_db.commit()
        
        # Handler executes with its own context
        result = await handler(
            job_id=job_id,
            progress_callback=async_progress_callback,
            **kwargs
        )
        
        # Final status update with new session
        async with AsyncSessionLocal() as final_db:
            await self._update_job_status_with_session(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result=result,
                message="Job completed successfully",
                db=final_db
            )
            await final_db.commit()
```

## Guidelines for Creating New Jobs

### 1. Always Use Dedicated Sessions

Each database operation should have its own session scope:

```python
async def my_job_handler(job_id: str, progress_callback: Callable, **kwargs):
    # Good: Create a new session for this job
    async with AsyncSessionLocal() as db:
        # Do your database operations
        result = await some_operation(db)
        await db.commit()
    
    # Bad: Don't pass sessions between contexts
    # db = get_some_external_session()  # AVOID THIS
```

### 2. Progress Callbacks Should Be Self-Contained

When implementing progress callbacks, ensure they manage their own database sessions:

```python
# Good: Progress callback creates its own session
async def progress_callback(progress: int, message: str):
    async with AsyncSessionLocal() as db:
        await update_progress(db, progress, message)
        await db.commit()

# Bad: Don't reuse sessions from outer scope
db = outer_scope_session  # AVOID
async def progress_callback(progress: int, message: str):
    await update_progress(db, progress, message)  # This will fail
```

### 3. Complete Operations Before Session Closes

Ensure all database operations complete before the session context exits:

```python
# Good: Complete all operations within session scope
async with AsyncSessionLocal() as db:
    plan = await create_plan(db)
    changes = list(plan.changes)  # Force load lazy relationships
    await db.commit()
    return {"plan_id": plan.id, "changes": len(changes)}

# Bad: Accessing lazy-loaded attributes after session closes
async with AsyncSessionLocal() as db:
    plan = await create_plan(db)
    await db.commit()
return {"changes": len(plan.changes)}  # This might fail
```

### 4. Handle Exceptions with Proper Session Management

```python
async def my_job_handler(job_id: str, **kwargs):
    try:
        async with AsyncSessionLocal() as db:
            # Do work
            await db.commit()
    except Exception as e:
        # Use a new session for error handling
        async with AsyncSessionLocal() as error_db:
            await log_error(error_db, str(e))
            await error_db.commit()
        raise
```

## Debugging Greenlet Errors

### 1. Check the Stack Trace

Look for where the error originates:
- Is it in a progress callback?
- Is it after a session was closed?
- Is it in error handling code?

### 2. Identify Session Boundaries

Map out where sessions are created and closed:
```python
# Add debug logging
logger.debug(f"Creating session in {function_name}")
async with AsyncSessionLocal() as db:
    logger.debug(f"Session active in {function_name}")
    # operations
logger.debug(f"Session closed in {function_name}")
```

### 3. Look for Common Patterns

- **Lazy Loading**: Accessing relationships after session closes
- **Shared Sessions**: Passing sessions between functions
- **Callbacks**: Progress or error callbacks using outer scope sessions
- **Error Handlers**: Exception handling trying to use closed sessions

### 4. Test in Isolation

Create a minimal test case:
```python
async def test_job_isolation():
    # Test that your job handler works in isolation
    await my_job_handler(
        job_id="test-123",
        progress_callback=lambda p, m: print(f"{p}%: {m}"),
        **test_kwargs
    )
```

## Prevention Checklist

Before deploying a new job handler, verify:

- [ ] Each database operation uses its own `async with AsyncSessionLocal()` block
- [ ] Progress callbacks create their own sessions
- [ ] No sessions are passed between functions or stored in class attributes
- [ ] All lazy-loaded relationships are accessed before session closes
- [ ] Error handling uses new sessions, not the failed session
- [ ] The job handler can run independently without external session dependencies

## Example: Safe Job Handler Template

```python
async def safe_job_handler(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    **kwargs
) -> dict[str, Any]:
    """Template for a greenlet-safe job handler."""
    logger.info(f"Starting job {job_id}")
    
    try:
        # Progress update with isolated session
        await progress_callback(0, "Starting job")
        
        # Main work with its own session
        async with AsyncSessionLocal() as db:
            # Do your actual work here
            result = await perform_work(db, **kwargs)
            
            # Force load any lazy relationships while session is active
            if hasattr(result, 'relationships'):
                _ = list(result.relationships)
            
            await db.commit()
            
        # Progress update with isolated session
        await progress_callback(100, "Job completed")
        
        return {
            "status": "success",
            "result": result.id if hasattr(result, 'id') else str(result)
        }
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        
        # Error handling with its own session
        async with AsyncSessionLocal() as error_db:
            await log_job_error(error_db, job_id, str(e))
            await error_db.commit()
        
        raise
```

## Additional Resources

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Greenlet Context Error Explanation](https://sqlalche.me/e/20/xd2s)
- [AsyncIO Best Practices](https://docs.python.org/3/library/asyncio-task.html)

## Summary

The key to avoiding greenlet errors is maintaining proper session isolation. Each async context should manage its own database session lifecycle. Never pass sessions between contexts, and always ensure operations complete before sessions close. When in doubt, create a new session.