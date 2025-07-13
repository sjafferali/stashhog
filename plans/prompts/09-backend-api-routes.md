# Task 09: Backend API Routes Implementation

## Current State
- Core services are implemented (sync, analysis, jobs)
- Basic route structure exists
- No actual endpoint implementations
- No request/response models

## Objective
Implement all API endpoints with proper request validation, response models, error handling, and documentation.

## Requirements

### Request/Response Schemas

1. **app/api/schemas/common.py** - Common schemas:
   ```python
   class PaginationParams(BaseModel):
       page: int = Field(1, ge=1)
       per_page: int = Field(50, ge=1, le=100)
       sort_by: Optional[str] = None
       sort_order: Literal["asc", "desc"] = "asc"
       
   class SuccessResponse(BaseModel):
       success: bool = True
       message: Optional[str] = None
       
   class ErrorResponse(BaseModel):
       success: bool = False
       error: str
       detail: Optional[str] = None
       request_id: Optional[str] = None
       
   class PaginatedResponse(BaseModel, Generic[T]):
       items: List[T]
       total: int
       page: int
       per_page: int
       pages: int
   ```

2. **app/api/schemas/scene.py** - Scene schemas:
   ```python
   class SceneBase(BaseModel):
       id: str
       title: str
       paths: List[str]
       organized: bool
       details: Optional[str]
       created_date: datetime
       scene_date: Optional[datetime]
       
   class SceneResponse(SceneBase):
       studio: Optional[StudioResponse]
       performers: List[PerformerResponse]
       tags: List[TagResponse]
       last_synced: datetime
       
   class SceneFilter(BaseModel):
       search: Optional[str] = None
       studio_id: Optional[str] = None
       performer_ids: Optional[List[str]] = None
       tag_ids: Optional[List[str]] = None
       organized: Optional[bool] = None
       date_from: Optional[datetime] = None
       date_to: Optional[datetime] = None
   ```

3. **app/api/schemas/analysis.py** - Analysis schemas:
   ```python
   class AnalysisRequest(BaseModel):
       scene_ids: Optional[List[str]] = None
       filters: Optional[SceneFilter] = None
       options: AnalysisOptions
       plan_name: str
       
   class ChangePreview(BaseModel):
       field: str
       action: str
       current_value: Any
       proposed_value: Any
       confidence: float
       
   class SceneChanges(BaseModel):
       scene_id: str
       scene_title: str
       changes: List[ChangePreview]
       
   class PlanResponse(BaseModel):
       id: int
       name: str
       status: str
       created_at: datetime
       total_scenes: int
       total_changes: int
       metadata: Dict
       
   class PlanDetailResponse(PlanResponse):
       scenes: List[SceneChanges]
   ```

### Scene Routes Implementation

4. **app/api/routes/scenes.py** - Complete implementation:
   ```python
   @router.get("/scenes", response_model=PaginatedResponse[SceneResponse])
   async def list_scenes(
       pagination: PaginationParams = Depends(),
       filters: SceneFilter = Depends(),
       db: Session = Depends(get_db)
   ):
       """List scenes with pagination and filters"""
       # Implementation:
       # 1. Build query with filters
       # 2. Apply pagination
       # 3. Transform to response models
       # 4. Return paginated response
       
   @router.get("/scenes/{scene_id}", response_model=SceneResponse)
   async def get_scene(
       scene_id: str,
       db: Session = Depends(get_db)
   ):
       """Get single scene by ID"""
       # Implementation:
       # 1. Query scene with relationships
       # 2. Handle not found
       # 3. Transform to response model
       
   @router.post("/scenes/sync")
   async def sync_scenes(
       background: bool = True,
       incremental: bool = True,
       job_queue: JobQueue = Depends(get_job_queue),
       db: Session = Depends(get_db)
   ):
       """Trigger scene synchronization"""
       # Implementation:
       # 1. If background, queue job
       # 2. Else run sync directly
       # 3. Return job ID or result
       
   @router.post("/scenes/{scene_id}/resync")
   async def resync_scene(
       scene_id: str,
       sync_service: SyncService = Depends(get_sync_service),
       db: Session = Depends(get_db)
   ):
       """Resync specific scene"""
       # Implementation:
       # 1. Verify scene exists
       # 2. Run sync for single scene
       # 3. Return updated scene
   ```

### Analysis Routes Implementation

5. **app/api/routes/analysis.py** - Complete implementation:
   ```python
   @router.post("/analysis/generate")
   async def generate_analysis(
       request: AnalysisRequest,
       background: bool = True,
       job_queue: JobQueue = Depends(get_job_queue),
       db: Session = Depends(get_db)
   ):
       """Generate analysis plan for scenes"""
       # Implementation:
       # 1. Validate scene IDs or filters
       # 2. Queue analysis job
       # 3. Return job ID
       
   @router.get("/analysis/plans", response_model=PaginatedResponse[PlanResponse])
   async def list_plans(
       pagination: PaginationParams = Depends(),
       status: Optional[str] = None,
       db: Session = Depends(get_db)
   ):
       """List analysis plans"""
       # Implementation:
       # 1. Query plans with filters
       # 2. Apply pagination
       # 3. Transform to response models
       
   @router.get("/analysis/plans/{plan_id}", response_model=PlanDetailResponse)
   async def get_plan(
       plan_id: int,
       db: Session = Depends(get_db)
   ):
       """Get plan with all changes"""
       # Implementation:
       # 1. Query plan with changes
       # 2. Group changes by scene
       # 3. Transform to response model
       
   @router.post("/analysis/plans/{plan_id}/apply")
   async def apply_plan(
       plan_id: int,
       scene_ids: Optional[List[str]] = None,
       background: bool = True,
       job_queue: JobQueue = Depends(get_job_queue),
       db: Session = Depends(get_db)
   ):
       """Apply plan changes"""
       # Implementation:
       # 1. Verify plan exists and status
       # 2. Queue apply job
       # 3. Return job ID
       
   @router.patch("/analysis/changes/{change_id}")
   async def update_change(
       change_id: int,
       proposed_value: Any,
       db: Session = Depends(get_db)
   ):
       """Update individual change"""
       # Implementation:
       # 1. Verify change exists
       # 2. Update proposed value
       # 3. Return updated change
   ```

### Job Routes Implementation

6. **app/api/routes/jobs.py** - Complete implementation:
   ```python
   @router.get("/jobs", response_model=List[JobResponse])
   async def list_jobs(
       status: Optional[str] = None,
       job_type: Optional[str] = None,
       limit: int = Query(50, le=100),
       db: Session = Depends(get_db)
   ):
       """List recent jobs"""
       # Implementation:
       # 1. Query jobs with filters
       # 2. Order by created_at desc
       # 3. Transform to response models
       
   @router.get("/jobs/{job_id}", response_model=JobDetailResponse)
   async def get_job(
       job_id: str,
       db: Session = Depends(get_db),
       job_queue: JobQueue = Depends(get_job_queue)
   ):
       """Get job details"""
       # Implementation:
       # 1. Get from queue if active
       # 2. Else get from database
       # 3. Return detailed status
       
   @router.delete("/jobs/{job_id}")
   async def cancel_job(
       job_id: str,
       job_queue: JobQueue = Depends(get_job_queue),
       db: Session = Depends(get_db)
   ):
       """Cancel running job"""
       # Implementation:
       # 1. Check if job is running
       # 2. Cancel if possible
       # 3. Update database status
       
   @router.websocket("/jobs/{job_id}/ws")
   async def job_progress_ws(
       websocket: WebSocket,
       job_id: str,
       manager: WebSocketManager = Depends(get_websocket_manager)
   ):
       """WebSocket for real-time job progress"""
       # Implementation:
       # 1. Accept WebSocket connection
       # 2. Subscribe to job updates
       # 3. Send current status
       # 4. Stream updates until complete
   ```

### Settings Routes Implementation

7. **app/api/routes/settings.py** - Complete implementation:
   ```python
   @router.get("/settings", response_model=Dict[str, Any])
   async def get_settings(
       db: Session = Depends(get_db)
   ):
       """Get all application settings"""
       # Implementation:
       # 1. Query all settings
       # 2. Transform to dict
       # 3. Mask sensitive values
       
   @router.put("/settings")
   async def update_settings(
       settings: Dict[str, Any],
       db: Session = Depends(get_db)
   ):
       """Update application settings"""
       # Implementation:
       # 1. Validate setting keys
       # 2. Update values
       # 3. Reload configuration
       
   @router.post("/settings/test-stash")
   async def test_stash_connection(
       url: Optional[str] = None,
       api_key: Optional[str] = None,
       stash_service: StashService = Depends(get_stash_service)
   ):
       """Test Stash connection"""
       # Implementation:
       # 1. Use provided or saved credentials
       # 2. Test connection
       # 3. Return status and version
       
   @router.post("/settings/test-openai")
   async def test_openai_connection(
       api_key: Optional[str] = None,
       model: Optional[str] = None
   ):
       """Test OpenAI connection"""
       # Implementation:
       # 1. Use provided or saved credentials
       # 2. Make test API call
       # 3. Return status and model info
   ```

### Entity Routes

8. **app/api/routes/entities.py** - Performer, tag, studio routes:
   ```python
   @router.get("/performers", response_model=List[PerformerResponse])
   async def list_performers(
       search: Optional[str] = None,
       db: Session = Depends(get_db)
   ):
       """List all performers"""
       
   @router.get("/tags", response_model=List[TagResponse])
   async def list_tags(
       search: Optional[str] = None,
       db: Session = Depends(get_db)
   ):
       """List all tags"""
       
   @router.get("/studios", response_model=List[StudioResponse])
   async def list_studios(
       search: Optional[str] = None,
       db: Session = Depends(get_db)
   ):
       """List all studios"""
   ```

### Error Handling

9. **app/api/error_handlers.py** - Global error handlers:
   ```python
   @app.exception_handler(ValidationError)
   async def validation_exception_handler(
       request: Request,
       exc: ValidationError
   ):
       """Handle Pydantic validation errors"""
       
   @app.exception_handler(HTTPException)
   async def http_exception_handler(
       request: Request,
       exc: HTTPException
   ):
       """Handle HTTP exceptions"""
       
   @app.exception_handler(StashHogException)
   async def app_exception_handler(
       request: Request,
       exc: StashHogException
   ):
       """Handle application exceptions"""
   ```

### API Documentation

10. **app/api/docs.py** - Enhanced API docs:
    ```python
    # Custom OpenAPI schema
    # Add examples for all endpoints
    # Include authentication docs
    # Add response examples
    ```

## Expected Outcome

After completing this task:
- All API endpoints are fully implemented
- Request validation works properly
- Responses follow consistent format
- Errors are handled gracefully
- WebSocket endpoints work
- API documentation is complete

## Integration Points
- Routes use all services
- Integrated with job queue
- WebSocket manager for real-time
- Database sessions managed
- Settings affect behavior

## Success Criteria
1. All endpoints return correct data
2. Validation rejects invalid input
3. Pagination works correctly
4. Filters apply properly
5. WebSocket streams updates
6. Errors return proper status codes
7. API docs show all endpoints
8. Examples work in Swagger UI
9. Performance is acceptable