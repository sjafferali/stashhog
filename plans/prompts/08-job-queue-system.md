# Task 08: Job Queue System Implementation

## Current State
- Analysis and sync services exist but run synchronously
- Job model defined in database
- No background processing capability
- No real-time progress updates

## Objective
Implement a simple, dependency-free background job system using Python's asyncio, with job tracking, progress reporting, and WebSocket updates.

## Requirements

### Core Job System

1. **app/core/jobs/job_queue.py** - Main job queue:
   ```python
   class JobQueue:
       def __init__(self, max_workers: int = 3):
           self.queue: asyncio.Queue = asyncio.Queue()
           self.workers: List[asyncio.Task] = []
           self.active_jobs: Dict[str, Job] = {}
           self.max_workers = max_workers
           
       async def start(self):
           """Start worker tasks"""
           
       async def stop(self):
           """Gracefully stop all workers"""
           
       async def enqueue(
           self,
           job_type: str,
           job_func: Callable,
           job_args: Dict,
           job_id: Optional[str] = None
       ) -> str:
           """Add job to queue"""
           
       async def cancel_job(self, job_id: str) -> bool:
           """Cancel a running job"""
           
       async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
           """Get current job status"""
   ```

### Job Definition

2. **app/core/jobs/models.py** - Job models:
   ```python
   @dataclass
   class JobDefinition:
       id: str
       type: str  # "sync", "analysis", "apply_plan"
       func: Callable
       args: Dict
       created_at: datetime
       
   @dataclass
   class JobStatus:
       id: str
       type: str
       status: str  # "pending", "running", "completed", "failed", "cancelled"
       progress: int  # 0-100
       total_items: Optional[int]
       processed_items: int
       message: Optional[str]
       result: Optional[Any]
       error: Optional[str]
       started_at: Optional[datetime]
       completed_at: Optional[datetime]
   ```

### Job Worker

3. **app/core/jobs/worker.py** - Worker implementation:
   ```python
   class JobWorker:
       def __init__(
           self,
           queue: asyncio.Queue,
           job_registry: JobRegistry
       ):
           self.queue = queue
           self.registry = job_registry
           self.current_job: Optional[JobDefinition] = None
           
       async def run(self):
           """Main worker loop"""
           while True:
               try:
                   job = await self.queue.get()
                   await self.execute_job(job)
               except asyncio.CancelledError:
                   break
               except Exception as e:
                   logging.error(f"Worker error: {e}")
                   
       async def execute_job(self, job: JobDefinition):
           """Execute a single job"""
           try:
               # Update status to running
               await self.update_job_status(job.id, "running")
               
               # Execute with progress tracking
               result = await job.func(**job.args)
               
               # Update status to completed
               await self.update_job_status(
                   job.id, 
                   "completed",
                   result=result
               )
           except Exception as e:
               await self.update_job_status(
                   job.id,
                   "failed", 
                   error=str(e)
               )
   ```

### Job Registry

4. **app/core/jobs/registry.py** - Job type registry:
   ```python
   class JobRegistry:
       def __init__(self):
           self.job_types: Dict[str, JobType] = {}
           
       def register(
           self,
           job_type: str,
           handler: Callable,
           description: str
       ):
           """Register a job type"""
           
       def get_handler(self, job_type: str) -> Callable:
           """Get handler for job type"""
           
   # Decorator for registering jobs
   def job(job_type: str, description: str):
       def decorator(func):
           registry.register(job_type, func, description)
           return func
       return decorator
   ```

### Progress Tracking

5. **app/core/jobs/progress.py** - Progress reporter:
   ```python
   class ProgressReporter:
       def __init__(self, job_id: str, total_items: Optional[int] = None):
           self.job_id = job_id
           self.total_items = total_items
           self.processed_items = 0
           self._last_update = time.time()
           
       async def update(
           self,
           processed: int = 1,
           message: Optional[str] = None
       ):
           """Update progress and notify listeners"""
           self.processed_items += processed
           
           # Throttle updates (max 2 per second)
           if time.time() - self._last_update < 0.5:
               return
               
           progress = self._calculate_progress()
           await self._notify_progress(progress, message)
           self._last_update = time.time()
           
       def _calculate_progress(self) -> int:
           """Calculate percentage progress"""
           if self.total_items:
               return int((self.processed_items / self.total_items) * 100)
           return 0
           
       async def _notify_progress(
           self,
           progress: int,
           message: Optional[str]
       ):
           """Send progress via WebSocket"""
           await websocket_manager.send_job_update(
               self.job_id,
               {
                   "progress": progress,
                   "processed": self.processed_items,
                   "total": self.total_items,
                   "message": message
               }
           )
   ```

### WebSocket Manager

6. **app/core/websocket/manager.py** - WebSocket handling:
   ```python
   class WebSocketManager:
       def __init__(self):
           self.active_connections: Dict[str, List[WebSocket]] = {}
           
       async def connect(
           self,
           websocket: WebSocket,
           job_id: str
       ):
           """Connect client to job updates"""
           await websocket.accept()
           if job_id not in self.active_connections:
               self.active_connections[job_id] = []
           self.active_connections[job_id].append(websocket)
           
       def disconnect(self, websocket: WebSocket, job_id: str):
           """Remove client connection"""
           if job_id in self.active_connections:
               self.active_connections[job_id].remove(websocket)
               
       async def send_job_update(
           self,
           job_id: str,
           data: Dict
       ):
           """Send update to all connected clients"""
           if job_id in self.active_connections:
               for connection in self.active_connections[job_id]:
                   try:
                       await connection.send_json(data)
                   except:
                       # Client disconnected
                       pass
   ```

### Job Handlers

7. **app/jobs/sync_job.py** - Sync job implementation:
   ```python
   @job("sync_all", "Full synchronization from Stash")
   async def sync_all_job(
       job_id: str,
       force: bool = False,
       **kwargs
   ):
       """Execute full sync as background job"""
       progress = ProgressReporter(job_id)
       
       # Get services
       sync_service = get_sync_service()
       
       # Execute sync with progress
       result = await sync_service.sync_all(
           job_id=job_id,
           force=force,
           progress_callback=progress.update
       )
       
       return result.dict()
   ```

8. **app/jobs/analysis_job.py** - Analysis job:
   ```python
   @job("analyze_scenes", "Analyze scenes for metadata")
   async def analyze_scenes_job(
       job_id: str,
       scene_ids: Optional[List[str]] = None,
       options: Dict = None,
       **kwargs
   ):
       """Execute scene analysis as background job"""
       progress = ProgressReporter(job_id)
       
       # Get services
       analysis_service = get_analysis_service()
       
       # Convert options
       analysis_options = AnalysisOptions(**options) if options else None
       
       # Execute analysis
       plan = await analysis_service.analyze_scenes(
           scene_ids=scene_ids,
           options=analysis_options,
           job_id=job_id,
           progress_callback=progress.update
       )
       
       return {"plan_id": plan.id, "total_changes": len(plan.changes)}
   ```

### Database Integration

9. **app/repositories/job_repository.py** - Job persistence:
   ```python
   class JobRepository:
       async def create_job(
           self,
           job_id: str,
           job_type: str,
           db: Session
       ) -> Job:
           """Create job record"""
           
       async def update_job_status(
           self,
           job_id: str,
           status: str,
           progress: Optional[int] = None,
           result: Optional[Dict] = None,
           error: Optional[str] = None,
           db: Session = None
       ) -> Job:
           """Update job status"""
           
       async def get_job(
           self,
           job_id: str,
           db: Session
       ) -> Optional[Job]:
           """Get job by ID"""
           
       async def list_jobs(
           self,
           status: Optional[str] = None,
           job_type: Optional[str] = None,
           limit: int = 50,
           db: Session = None
       ) -> List[Job]:
           """List jobs with filters"""
   ```

### API Integration

10. **Update app/api/routes/jobs.py**:
    ```python
    @router.post("/jobs/{job_type}")
    async def create_job(
        job_type: str,
        request: Dict,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        job_queue: JobQueue = Depends(get_job_queue)
    ):
        """Create and queue a new job"""
        
    @router.get("/jobs/{job_id}")
    async def get_job(
        job_id: str,
        db: Session = Depends(get_db)
    ):
        """Get job status"""
        
    @router.delete("/jobs/{job_id}")
    async def cancel_job(
        job_id: str,
        job_queue: JobQueue = Depends(get_job_queue)
    ):
        """Cancel running job"""
        
    @router.websocket("/jobs/{job_id}/ws")
    async def job_websocket(
        websocket: WebSocket,
        job_id: str,
        manager: WebSocketManager = Depends(get_websocket_manager)
    ):
        """WebSocket for job progress"""
    ```

## Expected Outcome

After completing this task:
- Background jobs run asynchronously
- Progress is tracked and reported
- WebSocket provides real-time updates
- Jobs can be cancelled
- Job history is persisted
- No external dependencies required

## Integration Points
- Used by sync and analysis services
- Integrates with database for persistence
- WebSocket manager for real-time updates
- API routes for job management

## Success Criteria
1. Jobs run in background without blocking
2. Progress updates via WebSocket
3. Multiple jobs can run concurrently
4. Jobs can be cancelled cleanly
5. Job status persists across restarts
6. Memory usage is controlled
7. Errors are handled gracefully
8. Queue survives worker crashes
9. No external dependencies needed