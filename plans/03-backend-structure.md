# Task 03: Backend Application Structure

## Current State
- Basic FastAPI application exists in `backend/app/main.py`
- Core configuration in `backend/app/core/config.py`
- Empty directories for api, models, and services
- No routing or middleware configured

## Objective
Implement the complete backend application structure with proper routing, middleware, error handling, and dependency injection.

## Requirements

### Core Application Setup

1. **app/main.py** - Enhanced FastAPI application:
   ```python
   # Key components to implement:
   - FastAPI app instance with metadata
   - CORS middleware with configurable origins
   - Request ID middleware for tracking
   - Exception handlers for common errors
   - Lifespan context manager for startup/shutdown
   - API router inclusion with /api prefix
   - Static file serving for frontend (production)
   - Health and readiness endpoints
   ```

2. **app/core/config.py** - Comprehensive settings:
   ```python
   # Settings classes to implement:
   - AppSettings (name, version, debug, env)
   - DatabaseSettings (url, echo, pool_size)
   - StashSettings (url, api_key, timeout)
   - OpenAISettings (api_key, model, max_tokens)
   - SecuritySettings (secret_key, algorithm)
   - CORSSettings (origins, credentials, methods)
   - Settings (main class combining all above)
   ```

3. **app/core/dependencies.py** - Dependency injection:
   ```python
   # Dependencies to implement:
   - get_db() - Database session
   - get_settings() - Cached settings
   - get_stash_client() - Stash API client
   - get_openai_client() - OpenAI client
   - get_current_user() - Optional auth
   ```

### API Structure

4. **app/api/__init__.py** - API router aggregation:
   ```python
   # Main API router combining all routes
   ```

5. **app/api/routes/__init__.py** - Route exports

6. **app/api/routes/health.py** - Health check endpoints:
   - GET /health - Basic health check
   - GET /ready - Readiness check (DB, external services)
   - GET /version - Application version info

7. **app/api/routes/scenes.py** - Scene management:
   - GET /scenes - List with pagination and filters
   - GET /scenes/{id} - Get single scene
   - POST /scenes/sync - Trigger sync
   - POST /scenes/{id}/resync - Resync single scene

8. **app/api/routes/analysis.py** - Analysis operations:
   - POST /analysis/generate - Create analysis plan
   - GET /analysis/plans - List plans
   - GET /analysis/plans/{id} - Get plan details
   - POST /analysis/plans/{id}/apply - Apply changes
   - DELETE /analysis/plans/{id} - Delete plan

9. **app/api/routes/jobs.py** - Job management:
   - GET /jobs - List jobs with filters
   - GET /jobs/{id} - Get job details
   - DELETE /jobs/{id} - Cancel job
   - WebSocket /jobs/{id}/ws - Real-time updates

10. **app/api/routes/settings.py** - Application settings:
    - GET /settings - Get all settings
    - PUT /settings - Update settings
    - POST /settings/test-stash - Test Stash connection
    - POST /settings/test-openai - Test OpenAI

### Middleware and Error Handling

11. **app/core/middleware.py** - Custom middleware:
    ```python
    # Middleware to implement:
    - RequestIDMiddleware - Add X-Request-ID
    - LoggingMiddleware - Log all requests
    - TimingMiddleware - Add X-Process-Time
    ```

12. **app/core/exceptions.py** - Custom exceptions:
    ```python
    # Exceptions to implement:
    - StashHogException (base)
    - NotFoundError
    - ValidationError  
    - StashConnectionError
    - OpenAIError
    - JobNotFoundError
    - PlanNotFoundError
    ```

13. **app/core/error_handlers.py** - Exception handlers:
    - Handle custom exceptions with proper status codes
    - Handle validation errors from Pydantic
    - Handle unexpected errors with logging
    - Return consistent error response format

### Utilities

14. **app/core/logging.py** - Logging configuration:
    - Configure structured logging
    - Add request context
    - Different levels for dev/prod
    - Log rotation setup

15. **app/core/security.py** - Security utilities:
    - Password hashing (if needed)
    - JWT token handling (if needed)
    - API key validation
    - Rate limiting helpers

16. **app/core/pagination.py** - Pagination utilities:
    ```python
    # Classes to implement:
    - PaginationParams (page, size, sort)
    - PaginatedResponse (items, total, page, pages)
    - paginate() helper function
    ```

### Response Models

17. **app/api/schemas/__init__.py** - Pydantic schemas:
    ```python
    # Response models to implement:
    - HealthResponse
    - VersionResponse
    - ErrorResponse
    - SuccessResponse
    - PaginatedResponse (generic)
    ```

### Background Tasks

18. **app/core/tasks.py** - Task queue setup:
    ```python
    # Simple in-memory task queue:
    - TaskQueue class using asyncio.Queue
    - Task registration decorator
    - Task status tracking
    - Worker pool management
    ```

## Expected Outcome

After completing this task:
- Complete backend application structure is implemented
- All routes return proper responses (can be mocked)
- Middleware handles cross-cutting concerns
- Error handling is consistent and informative
- Dependency injection is properly configured
- Application is ready for service implementation

## Integration Points
- Routes are connected to (future) services
- Middleware integrates with all requests
- Dependencies are injected where needed
- Error handlers catch all exceptions
- Settings are accessible throughout app

## Success Criteria
1. FastAPI app starts without errors
2. All routes are accessible via /docs
3. Health check returns 200 OK
4. CORS is properly configured
5. Errors return consistent JSON format
6. Request IDs are added to all responses
7. Logging captures all requests
8. Settings load from environment
9. No import errors or circular dependencies