# Adding New Daemons

This guide explains how to create new daemons in StashHog, following best practices to avoid greenlet errors and ensure proper integration with the system.

## Overview

Daemons are long-running background processes that:
- Run continuously until explicitly stopped
- Can monitor system state and react to events
- Launch and orchestrate other jobs
- Provide real-time logging
- Maintain heartbeat for health monitoring

## Prerequisites

Before creating a daemon, ensure you understand:
- Python asyncio programming
- SQLAlchemy async sessions
- The difference between Jobs and Daemons (see `docs/jobs-vs-daemons.md`)
- Greenlet error prevention (see `docs/avoiding-greenlet-errors.md`)

## Step-by-Step Guide

### 1. Define the Daemon Type

Add your daemon type to the `DaemonType` enum in `backend/app/models/daemon.py`:

```python
class DaemonType(str, enum.Enum):
    TEST_DAEMON = "test_daemon"
    METADATA_GENERATE_WATCHER = "metadata_generate_watcher"
    YOUR_NEW_DAEMON = "your_new_daemon"  # Add your type here
```

### 2. Create the Daemon Class

Create a new file in `backend/app/daemons/` for your daemon:

```python
# backend/app/daemons/your_daemon.py
from typing import Optional, Set
import asyncio
import time
from app.daemons.base import BaseDaemon
from app.models.daemon import DaemonType, LogLevel
from app.core.database import AsyncSessionLocal
from app.models.job import Job, JobStatus, JobType

class YourDaemon(BaseDaemon):
    """
    Brief description of what your daemon does.
    
    Configuration:
        key1 (int): Description of config option 1
        key2 (str): Description of config option 2
    """
    
    daemon_type = DaemonType.YOUR_NEW_DAEMON
    
    async def on_start(self):
        """Initialize daemon-specific resources."""
        await super().on_start()
        # Initialize any daemon-specific state
        self.monitored_items = set()
        await self.log(LogLevel.INFO, "YourDaemon initialized")
    
    async def on_stop(self):
        """Clean up daemon-specific resources."""
        await self.log(LogLevel.INFO, "YourDaemon shutting down")
        # Clean up any resources
        await super().on_stop()
    
    async def run(self):
        """Main daemon execution loop."""
        # Get configuration with defaults
        check_interval = self.config.get("check_interval", 10)
        
        await self.log(LogLevel.INFO, f"YourDaemon started with config: {self.config}")
        
        while self.is_running:
            try:
                # Update heartbeat periodically
                await self.update_heartbeat()
                
                # Your main daemon logic here
                await self._do_work()
                
                # Sleep for the configured interval
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                # Graceful shutdown
                await self.log(LogLevel.INFO, "YourDaemon received shutdown signal")
                break
                
            except Exception as e:
                # Log errors but continue running
                await self.log(LogLevel.ERROR, f"YourDaemon error: {str(e)}")
                if self.is_running:
                    await asyncio.sleep(5)  # Back off on error
    
    async def _do_work(self):
        """Implement your daemon's core functionality."""
        # IMPORTANT: Always use dedicated sessions for database operations
        async with AsyncSessionLocal() as db:
            # Query for items to process
            items = await self._get_items_to_process(db)
            
            for item in items:
                if not self.is_running:
                    break
                    
                await self._process_item(item)
    
    async def _process_item(self, item):
        """Process a single item."""
        try:
            # Log what you're doing
            await self.log(LogLevel.DEBUG, f"Processing item: {item.id}")
            
            # Launch a job if needed
            async with AsyncSessionLocal() as db:
                job = await self._create_job(db, item)
                await db.commit()
                job_id = job.id
            
            # Track the job action
            await self.track_job_action(
                job_id=job_id,
                action=DaemonJobAction.LAUNCHED,
                reason=f"Processing item {item.id}"
            )
            
            # Add to monitoring if needed
            # NOTE: You should add job_id, not item.id to monitoring!
            self.monitored_jobs.add(job_id)  # Track the job, not the item
            
        except Exception as e:
            await self.log(LogLevel.ERROR, f"Failed to process item: {str(e)}")
```

### 3. Register the Daemon

Add your daemon to the daemon registry in `backend/app/daemons/__init__.py`:

```python
from app.daemons.test_daemon import TestDaemon
from app.daemons.your_daemon import YourDaemon  # Import your daemon

# Registry of all available daemon classes
DAEMON_CLASSES = {
    DaemonType.TEST_DAEMON: TestDaemon,
    DaemonType.YOUR_NEW_DAEMON: YourDaemon,  # Register your daemon
}
```

### 4. Create Initial Database Record

Add a data migration to create the daemon record:

```python
# backend/alembic/versions/xxx_add_your_daemon.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

def upgrade():
    # Insert daemon record
    op.execute(
        f"""
        INSERT INTO daemons (id, name, type, enabled, auto_start, status, configuration)
        VALUES (
            '{uuid.uuid4()}',
            'Your Daemon Name',
            'your_new_daemon',
            false,
            false,
            'STOPPED',
            '{{"check_interval": 10, "other_config": "value"}}'::jsonb
        )
        """
    )

def downgrade():
    op.execute("DELETE FROM daemons WHERE type = 'your_new_daemon'")
```

## Best Practices

### 1. Database Session Management

**ALWAYS** create new sessions for each operation:

```python
# ✅ CORRECT: New session for each operation
async def do_something(self):
    async with AsyncSessionLocal() as db:
        result = await db.execute(query)
        await db.commit()

# ❌ WRONG: Reusing sessions across contexts
self.db = AsyncSessionLocal()  # Never store sessions as attributes
```

### 2. Logging Guidelines

Use appropriate log levels:
- `DEBUG`: Detailed operational info
- `INFO`: Important state changes
- `WARNING`: Recoverable issues
- `ERROR`: Errors that need attention

```python
await self.log(LogLevel.DEBUG, "Checking for new items")
await self.log(LogLevel.INFO, f"Processing {len(items)} items")
await self.log(LogLevel.WARNING, "Queue is getting large")
await self.log(LogLevel.ERROR, f"Failed to process: {error}")
```

### 3. Heartbeat Management

Update heartbeat regularly to indicate daemon health:

```python
async def run(self):
    last_heartbeat = 0
    heartbeat_interval = 30  # seconds
    
    while self.is_running:
        current_time = time.time()
        
        if current_time - last_heartbeat >= heartbeat_interval:
            await self.update_heartbeat()
            last_heartbeat = current_time
        
        # Your work here
        await asyncio.sleep(1)
```

### 4. Configuration Handling

Always provide sensible defaults:

```python
# Get config with defaults
check_interval = self.config.get("check_interval", 10)
batch_size = self.config.get("batch_size", 100)
retry_count = self.config.get("retry_count", 3)

# Validate configuration
if check_interval < 1:
    await self.log(LogLevel.WARNING, "check_interval too low, using 1")
    check_interval = 1
```

### 5. Job Orchestration and Monitoring

#### Job Actions

StashHog tracks three types of job actions that daemons can record:

- **LAUNCHED**: When a daemon creates or starts a job
- **CANCELLED**: When a daemon cancels a job
- **MONITORED**: When a daemon detects a job it was tracking has completed

**Important**: Job monitoring is NOT automatic. Each daemon must explicitly implement monitoring for jobs it cares about.

#### Launching Jobs

When launching jobs from daemons:

```python
async def launch_job(self, job_type: JobType, metadata: dict):
    try:
        # Create job with dedicated session
        async with AsyncSessionLocal() as db:
            job = Job(
                id=str(uuid.uuid4()),
                type=job_type,
                status=JobStatus.PENDING,
                metadata=metadata
            )
            db.add(job)
            await db.commit()
            job_id = job.id
        
        # Track the action
        await self.track_job_action(
            job_id=job_id,
            action=DaemonJobAction.LAUNCHED,
            reason="Daemon initiated job"
        )
        
        # Submit to job service
        await self.job_service.submit_job(job_id)
        
        # Add to monitoring if you need to track completion
        self._monitored_jobs.add(job_id)
        
        return job_id
        
    except Exception as e:
        await self.log(LogLevel.ERROR, f"Failed to launch job: {e}")
        return None
```

#### Implementing Job Monitoring

To monitor jobs your daemon launches:

```python
class YourDaemon(BaseDaemon):
    async def on_start(self):
        await super().on_start()
        # Set to track jobs we're monitoring
        self._monitored_jobs: Set[str] = set()
    
    async def run(self):
        while self.is_running:
            try:
                # Your main work
                await self._do_work()
                
                # Check monitored jobs periodically
                await self._check_monitored_jobs()
                
                await asyncio.sleep(self.config.get("check_interval", 10))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.log(LogLevel.ERROR, f"Error: {e}")
    
    async def _check_monitored_jobs(self):
        """Check status of jobs we're monitoring."""
        if not self._monitored_jobs:
            return
        
        completed_jobs = set()
        
        async with AsyncSessionLocal() as db:
            for job_id in self._monitored_jobs:
                job = await db.get(Job, job_id)
                if not job:
                    completed_jobs.add(job_id)
                    continue
                
                # Check if job has finished
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    await self.log(
                        LogLevel.INFO,
                        f"Job {job_id} completed with status: {job.status}"
                    )
                    
                    # Track the monitoring action
                    await self.track_job_action(
                        job_id=job_id,
                        action=DaemonJobAction.MONITORED,
                        reason=f"Job completed with status {job.status}"
                    )
                    
                    # Optionally react based on job outcome
                    if job.status == JobStatus.FAILED:
                        await self._handle_failed_job(job)
                    
                    completed_jobs.add(job_id)
        
        # Remove completed jobs from monitoring
        self._monitored_jobs -= completed_jobs
```

#### Cancelling Jobs

If your daemon needs to cancel jobs:

```python
async def cancel_job(self, job_id: str, reason: str):
    try:
        # Use job service to cancel
        await self.job_service.cancel_job(job_id)
        
        # Track the cancellation
        await self.track_job_action(
            job_id=job_id,
            action=DaemonJobAction.CANCELLED,
            reason=reason
        )
        
        # Remove from monitoring
        self._monitored_jobs.discard(job_id)
        
    except Exception as e:
        await self.log(LogLevel.ERROR, f"Failed to cancel job: {e}")
```

### 6. Graceful Shutdown

Always handle shutdown gracefully:

```python
async def run(self):
    try:
        while self.is_running:
            # Your work
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        await self.log(LogLevel.INFO, "Shutting down gracefully")
        # Clean up resources
        await self._cleanup()
        raise  # Re-raise to properly cancel
```

### 7. Error Recovery

Implement proper error handling:

```python
async def run(self):
    consecutive_errors = 0
    max_errors = 5
    
    while self.is_running:
        try:
            await self._do_work()
            consecutive_errors = 0  # Reset on success
            
        except Exception as e:
            consecutive_errors += 1
            await self.log(LogLevel.ERROR, f"Error #{consecutive_errors}: {e}")
            
            if consecutive_errors >= max_errors:
                await self.log(LogLevel.ERROR, "Too many errors, stopping")
                self.is_running = False
                break
            
            # Exponential backoff
            await asyncio.sleep(min(2 ** consecutive_errors, 60))
```

## Testing Your Daemon

### 1. Unit Test Template

```python
# backend/tests/test_daemons/test_your_daemon.py
import pytest
from app.daemons.your_daemon import YourDaemon
from app.models.daemon import DaemonType, DaemonStatus

@pytest.mark.asyncio
async def test_your_daemon_initialization():
    config = {"check_interval": 5}
    daemon = YourDaemon(
        daemon_id="test-id",
        config=config
    )
    
    assert daemon.daemon_type == DaemonType.YOUR_NEW_DAEMON
    assert daemon.config == config
    assert daemon.status == DaemonStatus.STOPPED

@pytest.mark.asyncio
async def test_your_daemon_run(mock_db):
    daemon = YourDaemon("test-id", {})
    
    # Run for a short time
    run_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)
    
    # Stop the daemon
    await daemon.stop()
    await run_task
    
    # Verify logs were created
    assert len(daemon.get_logs()) > 0
```

### 2. Integration Testing

Test with the full daemon service:

```python
async def test_daemon_service_integration():
    from app.services.daemon_service import daemon_service
    
    # Start your daemon
    daemon_id = await daemon_service.start_daemon("your-daemon-id")
    
    # Let it run
    await asyncio.sleep(5)
    
    # Check status
    status = await daemon_service.get_daemon_status(daemon_id)
    assert status == DaemonStatus.RUNNING
    
    # Stop it
    await daemon_service.stop_daemon(daemon_id)
```

## Common Pitfalls to Avoid

### 1. Session Leaks

```python
# ❌ WRONG: Session leak
class BadDaemon(BaseDaemon):
    async def on_start(self):
        self.db = AsyncSessionLocal()  # This will cause greenlet errors!
```

### 2. Blocking Operations

```python
# ❌ WRONG: Blocking I/O
import time
time.sleep(10)  # This blocks the event loop!

# ✅ CORRECT: Async sleep
await asyncio.sleep(10)
```

### 3. Unhandled Exceptions

```python
# ❌ WRONG: Daemon crashes on error
async def run(self):
    while self.is_running:
        result = await risky_operation()  # If this fails, daemon stops!

# ✅ CORRECT: Handle exceptions
async def run(self):
    while self.is_running:
        try:
            result = await risky_operation()
        except Exception as e:
            await self.log(LogLevel.ERROR, str(e))
```

### 4. Resource Exhaustion

```python
# ❌ WRONG: Unbounded growth
self.processed_items.append(item)  # List grows forever!

# ✅ CORRECT: Bounded collections
from collections import deque
self.recent_items = deque(maxlen=1000)  # Limited size
```

## Monitoring and Debugging

### 1. Check Daemon Logs

```bash
# View daemon logs via API
curl http://localhost:8000/api/daemons/{daemon_id}/logs
```

### 2. Monitor Heartbeat

```sql
-- Check daemon health
SELECT name, status, last_heartbeat, 
       NOW() - last_heartbeat as time_since_heartbeat
FROM daemons
WHERE type = 'your_new_daemon';
```

### 3. Debug Configuration

```python
# Add debug mode to your daemon
if self.config.get("debug", False):
    await self.log(LogLevel.DEBUG, f"State: {self.__dict__}")
```

## Deployment Checklist

Before deploying your daemon:

- [ ] All database operations use dedicated sessions
- [ ] Heartbeat updates are implemented
- [ ] Graceful shutdown is handled
- [ ] Errors are logged but don't crash the daemon
- [ ] Configuration has sensible defaults
- [ ] Job monitoring is implemented if daemon launches jobs
- [ ] Job actions (LAUNCHED, MONITORED, CANCELLED) are tracked appropriately
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Documentation is updated
- [ ] Migration creates initial daemon record
- [ ] Daemon is registered in the registry

## Example: Complete TestDaemon

See `backend/app/daemons/test_daemon.py` for a complete example that demonstrates:
- All lifecycle methods
- Proper session management
- Job launching and monitoring
- Configuration handling
- Error recovery
- Heartbeat updates
- Multiple log levels
- Graceful shutdown

Use the TestDaemon as a template for your own daemons, as it follows all best practices and demonstrates every feature of the daemon system.