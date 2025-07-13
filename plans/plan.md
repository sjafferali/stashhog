# StashHog Implementation Plan

## Executive Summary

StashHog is a web-based application for managing and analyzing scene metadata in a Stash media server. It provides automated metadata detection, batch processing capabilities, and a user-friendly interface for reviewing and applying changes.

## Architecture Overview

### Technology Stack

#### Backend
- **Framework**: FastAPI (Python 3.9+)
  - Chosen for async support, automatic API documentation, and modern Python features
  - Built-in validation with Pydantic
  - WebSocket support for real-time updates

- **Database**: SQLite with SQLAlchemy ORM
  - No external dependencies
  - Sufficient for metadata storage and job tracking
  - Easy backup and portability

- **Background Jobs**: Custom async queue using asyncio
  - No Redis/Celery required
  - In-memory job queue with database persistence
  - Simple and maintainable

- **Key Libraries**:
  - `stashapi`: GraphQL client for Stash server
  - `openai`: AI-powered metadata detection
  - `python-multipart`: File upload support
  - `apscheduler`: Task scheduling

#### Frontend
- **Framework**: React 18 with TypeScript
  - Type safety and better developer experience
  - Modern hooks-based architecture
  - Strong ecosystem

- **UI Library**: Ant Design 5
  - Comprehensive component set
  - Professional appearance
  - Good accessibility

- **State Management**: Zustand
  - Lightweight (8KB)
  - No boilerplate
  - TypeScript friendly

- **Build Tool**: Vite
  - Fast development server
  - Optimized production builds
  - Native ES modules

## Core Features

### 1. Scene Management
- Browse and filter scenes from Stash server
- Display all metadata fields:
  - Scene ID, Title, Paths
  - Organized status
  - Performers, Tags, Studio
  - Details, Created Date, Scene Date
- Search and filter capabilities
- Pagination for large datasets

### 2. Sync Functionality
- **Full Sync**: Import all scenes from StashApp
- **Incremental Sync**: Update only changed scenes
- **Individual Resync**: Update specific scene by ID
- **Entity Sync**: Import performers, tags, studios

### 3. Analysis Engine
- Port logic from existing `analyze_scenes.py`
- AI-powered detection using OpenAI API
- Studio detection from file paths
- Performer name normalization
- Tag suggestions based on content
- Scene detail generation

### 4. Change Management
- Generate analysis plans showing proposed changes
- Visual diff viewer for each field
- Save plans for later review
- Bulk operations support
- Apply changes with confirmation
- Rollback capability

### 5. Task Scheduling
- Schedule regular sync operations
- Schedule batch analyses
- View scheduled tasks
- Manual trigger capability
- Task history and logs

### 6. Background Job System
- Async processing for long operations
- Real-time progress updates via WebSocket
- Job status tracking
- Error handling and retry logic
- Resource management

## Database Schema

### Core Tables

```sql
-- Scenes (cached from Stash)
CREATE TABLE scenes (
    id TEXT PRIMARY KEY,
    title TEXT,
    paths JSON,
    organized BOOLEAN,
    details TEXT,
    created_date TIMESTAMP,
    scene_date TIMESTAMP,
    studio_id TEXT,
    last_synced TIMESTAMP,
    FOREIGN KEY (studio_id) REFERENCES studios(id)
);

-- Performers
CREATE TABLE performers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    last_synced TIMESTAMP
);

-- Tags
CREATE TABLE tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    last_synced TIMESTAMP
);

-- Studios
CREATE TABLE studios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    last_synced TIMESTAMP
);

-- Many-to-many relationships
CREATE TABLE scene_performers (
    scene_id TEXT,
    performer_id TEXT,
    PRIMARY KEY (scene_id, performer_id)
);

CREATE TABLE scene_tags (
    scene_id TEXT,
    tag_id TEXT,
    PRIMARY KEY (scene_id, tag_id)
);

-- Analysis Plans
CREATE TABLE analysis_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    status TEXT DEFAULT 'draft'
);

-- Plan Changes
CREATE TABLE plan_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    scene_id TEXT,
    field TEXT,
    current_value JSON,
    proposed_value JSON,
    confidence FLOAT,
    applied BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (plan_id) REFERENCES analysis_plans(id)
);

-- Jobs
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    total INTEGER,
    result JSON,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Settings
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Tasks
CREATE TABLE scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    schedule TEXT NOT NULL,
    config JSON,
    enabled BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMP,
    next_run TIMESTAMP
);
```

## API Endpoints

### Scene Management
- `GET /api/scenes` - List scenes with filters
- `GET /api/scenes/{id}` - Get scene details
- `POST /api/scenes/sync` - Trigger full sync
- `POST /api/scenes/{id}/resync` - Resync specific scene

### Analysis
- `POST /api/analysis/generate` - Generate analysis plan
- `GET /api/analysis/plans` - List saved plans
- `GET /api/analysis/plans/{id}` - Get plan details
- `POST /api/analysis/plans/{id}/apply` - Apply plan changes
- `DELETE /api/analysis/plans/{id}` - Delete plan

### Jobs
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{id}` - Get job status
- `DELETE /api/jobs/{id}` - Cancel job
- `WS /api/jobs/{id}/progress` - WebSocket for progress

### Settings
- `GET /api/settings` - Get all settings
- `PUT /api/settings` - Update settings
- `POST /api/settings/test-connection` - Test Stash connection

### Scheduling
- `GET /api/schedules` - List scheduled tasks
- `POST /api/schedules` - Create schedule
- `PUT /api/schedules/{id}` - Update schedule
- `DELETE /api/schedules/{id}` - Delete schedule

## Security Considerations

1. **API Keys**: Store securely in database (encrypted)
2. **Authentication**: Optional basic auth for web UI
3. **Input Validation**: Pydantic models for all inputs
4. **SQL Injection**: Use SQLAlchemy ORM
5. **XSS Prevention**: React handles by default
6. **CORS**: Configure for production deployment

## Deployment Strategy

### Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Production (Docker)
- Multi-stage Dockerfile
- Nginx reverse proxy
- Single container deployment
- Environment variable configuration
- Health checks included

## Performance Considerations

1. **Database Indexes**: On scene_id, performer_id, tag_id
2. **Pagination**: Limit API responses
3. **Caching**: In-memory cache for frequently accessed data
4. **Batch Operations**: Process scenes in chunks
5. **WebSocket Throttling**: Limit update frequency

## Testing Strategy

1. **Backend**:
   - Unit tests with pytest
   - Integration tests for API endpoints
   - Mock Stash API for testing

2. **Frontend**:
   - Component tests with React Testing Library
   - E2E tests with Playwright
   - Visual regression tests

3. **CI/CD**:
   - Run all tests on PR
   - Type checking (mypy, TypeScript)
   - Linting (ruff, ESLint)
   - Build Docker image

## Future Enhancements

1. **Plugin System**: Allow custom analyzers
2. **Bulk Import/Export**: CSV/JSON support
3. **Advanced Filtering**: Complex query builder
4. **Webhooks**: Notify external systems
5. **Multi-user Support**: Role-based access
6. **Backup/Restore**: Automated backups
7. **Metrics Dashboard**: Usage statistics
8. **Mobile UI**: Responsive design improvements