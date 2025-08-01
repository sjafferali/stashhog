# API Route Development Guidelines

## Overview

This document provides comprehensive guidelines for adding new API routes to the application. Following these practices will help prevent common issues and maintain consistency across the codebase.

## Table of Contents

1. [Route Ordering](#route-ordering)
2. [Naming Conventions](#naming-conventions)
3. [Error Handling](#error-handling)
4. [Response Models](#response-models)
5. [Authentication & Authorization](#authentication--authorization)
6. [Testing](#testing)
7. [Documentation](#documentation)

## Route Ordering

### The Problem

FastAPI matches routes in the order they are defined. This can lead to unexpected behavior when dynamic path parameters conflict with static routes.

### Best Practices

#### Order Routes from Most Specific to Least Specific

Always define static routes before dynamic routes:

```python
# ✅ CORRECT: Static routes first
@router.get("/recent-processed-torrents")
async def get_recent_processed_torrents():
    pass

@router.get("/stats")
async def get_stats():
    pass

# Dynamic route last
@router.get("/{job_id}")
async def get_job(job_id: str):
    pass
```

#### Common Mistake Example

```python
# ❌ WRONG: Dynamic route catches everything
@router.get("/{job_id}")
async def get_job(job_id: str):
    # This catches ALL requests to /jobs/*
    pass

@router.get("/recent-processed-torrents")
async def get_recent_processed_torrents():
    # This will NEVER be reached!
    pass
```

A request to `/jobs/recent-processed-torrents` will match the first route, treating "recent-processed-torrents" as a `job_id` parameter.

## Naming Conventions

### URL Path Conventions

- Use kebab-case for multi-word paths: `/recent-processed-torrents`
- Use plural nouns for collections: `/jobs`, `/scenes`
- Use singular nouns for individual resources: `/job/{id}`, `/scene/{id}`
- Be consistent with existing patterns in the codebase

### Function Naming

```python
# Collection endpoints
async def list_jobs()      # GET /jobs
async def create_job()     # POST /jobs

# Individual resource endpoints
async def get_job()        # GET /jobs/{id}
async def update_job()     # PUT/PATCH /jobs/{id}
async def delete_job()     # DELETE /jobs/{id}

# Action endpoints
async def cancel_job()     # POST /jobs/{id}/cancel
async def retry_job()      # POST /jobs/{id}/retry
```

## Error Handling

### Consistent Error Responses

Always use HTTPException with appropriate status codes:

```python
from fastapi import HTTPException, status

# Resource not found
if not job:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Job {job_id} not found"
    )

# Invalid request
if job.status not in ["failed", "cancelled"]:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Cannot retry a {job.status} job"
    )

# Conflict
if existing_job:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Job already running: {existing_job.id}"
    )
```

## Response Models

### Use Pydantic Models

Define response models for type safety and automatic documentation:

```python
from pydantic import BaseModel
from typing import List, Optional

class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    progress: float
    created_at: datetime
    
class JobsListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int

@router.get("", response_model=JobsListResponse)
async def list_jobs() -> JobsListResponse:
    pass
```

### Consistent Response Structure

For action endpoints, use a consistent structure:

```python
# Success response
{
    "success": true,
    "message": "Operation completed successfully",
    "data": { ... }  # Optional additional data
}

# Error response (handled by HTTPException)
{
    "detail": "Error message",
    "status_code": 400
}
```

## Authentication & Authorization

### Apply Appropriate Security

```python
from app.core.dependencies import get_current_user

# Public endpoint
@router.get("/public/stats")
async def get_public_stats():
    pass

# Protected endpoint
@router.post("/admin/cleanup", dependencies=[Depends(get_current_user)])
async def trigger_cleanup():
    pass
```

## Testing

### Write Tests for New Routes

```python
def test_new_endpoint():
    """Test the new endpoint works correctly"""
    response = client.get("/api/jobs/recent-processed-torrents")
    assert response.status_code == 200
    assert "torrents" in response.json()

def test_route_ordering():
    """Ensure static routes aren't shadowed by dynamic routes"""
    response = client.get("/api/jobs/recent-processed-torrents")
    # Should not get "Job recent-processed-torrents not found" error
    assert "not found" not in response.json().get("detail", "").lower()
```

## Documentation

### Add Docstrings

Every endpoint should have a clear docstring:

```python
@router.get("/recent-processed-torrents")
async def get_recent_processed_torrents(
    limit: int = Query(10, le=50, description="Maximum number of torrents to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get recently processed torrents with file counts.

    Returns a summary of the most recently processed torrents, showing:
    - Torrent name
    - Number of files processed
    - When they were processed
    """
    pass
```

### Update API Documentation

- Add new endpoints to `docs/endpoints.md`
- Update Postman/Insomnia collections if maintained
- Document any breaking changes in CHANGELOG

## Checklist for Adding New Routes

- [ ] Route is defined in the correct order (static before dynamic)
- [ ] Route follows naming conventions
- [ ] Proper error handling with appropriate status codes
- [ ] Response model defined (if returning data)
- [ ] Authentication/authorization applied if needed
- [ ] Docstring added to endpoint function
- [ ] Tests written for the new endpoint
- [ ] API documentation updated

## Common Pitfalls to Avoid

1. **Adding routes at the bottom of the file** - Check if dynamic routes exist above
2. **Inconsistent naming** - Follow existing patterns
3. **Missing error handling** - Always handle edge cases
4. **No response model** - Define models for type safety
5. **Forgetting tests** - Write tests for new functionality

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [REST API Best Practices](https://restfulapi.net/)