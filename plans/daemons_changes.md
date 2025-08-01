# Daemons Feature Implementation Summary

## Overview

This document provides a comprehensive summary of the Daemons feature implementation in StashHog. Daemons are continuous background processes that run indefinitely, monitor system events, and can orchestrate other jobs. They differ from regular jobs which have a clear start/end and scheduled tasks which run periodically.

## Architecture Overview

### Naming Decision
- **Chosen Name**: "Daemons" (over Supervisors, Watchers, Monitors, Orchestrators, Services)
- **Rationale**: Classic term that clearly indicates continuous background processes

### Concurrency Model
- Uses Python `asyncio` (not threads/greenlets) to avoid greenlet errors
- No hard limit on concurrent daemons (limited by system resources)
- Recommended soft limit: 10-20 daemons per server
- Each daemon runs as an asyncio task

## Backend Implementation

### 1. Database Schema

Three new PostgreSQL tables were created:

#### `daemons` table
- `id` (UUID) - Primary key
- `name` (VARCHAR 255) - Unique daemon name
- `type` (VARCHAR 100) - Daemon type enum
- `enabled` (BOOLEAN) - Whether daemon is enabled
- `auto_start` (BOOLEAN) - Auto-start on system startup
- `status` (VARCHAR 50) - Current status (STOPPED/RUNNING/ERROR)
- `configuration` (JSONB) - Daemon-specific configuration
- `started_at` (TIMESTAMP) - When daemon was last started
- `last_heartbeat` (TIMESTAMP) - Last heartbeat for health monitoring
- `created_at`, `updated_at` (TIMESTAMP) - Audit timestamps

#### `daemon_logs` table
- `id` (UUID) - Primary key
- `daemon_id` (UUID) - Foreign key to daemons
- `level` (VARCHAR 20) - Log level (DEBUG/INFO/WARNING/ERROR)
- `message` (TEXT) - Log message
- `created_at` (TIMESTAMP) - When log was created

#### `daemon_job_history` table
- `id` (UUID) - Primary key
- `daemon_id` (UUID) - Foreign key to daemons
- `job_id` (UUID) - Foreign key to jobs
- `action` (VARCHAR 50) - Action taken (LAUNCHED/CANCELLED/MONITORED)
- `reason` (TEXT) - Optional reason for action
- `created_at` (TIMESTAMP) - When action occurred

### 2. Backend Models

Located in `backend/app/models/daemon.py`:

#### Enums
- `DaemonType`: TEST_DAEMON, METADATA_GENERATE_WATCHER
- `DaemonStatus`: STOPPED, RUNNING, ERROR
- `LogLevel`: DEBUG, INFO, WARNING, ERROR
- `DaemonJobAction`: LAUNCHED, CANCELLED, MONITORED

#### Models
- `Daemon`: Main daemon entity with relationships to logs and job history
- `DaemonLog`: Individual log entries
- `DaemonJobHistory`: Tracks all job-related actions

### 3. Daemon Framework

#### Base Daemon (`backend/app/daemons/base.py`)
Abstract base class providing:
- Lifecycle management (`start()`, `stop()`, `on_start()`, `on_stop()`)
- Logging with WebSocket broadcasting
- Heartbeat updates
- Job action tracking
- Configuration handling
- Error recovery wrapper

Key design principles:
- Each database operation uses a dedicated AsyncSession
- No sessions are stored as attributes or passed between contexts
- Graceful shutdown handling with asyncio.CancelledError
- Automatic status updates in database

#### Test Daemon (`backend/app/daemons/test_daemon.py`)
Comprehensive example daemon demonstrating:
- Heartbeat updates every 10 seconds (configurable)
- Multi-level logging (DEBUG, INFO, WARNING, ERROR)
- Job launching and monitoring
- Memory usage reporting (using psutil)
- Error simulation for testing
- Configuration: `log_interval`, `job_interval`, `heartbeat_interval`, `simulate_errors`

### 4. Daemon Service

`backend/app/services/daemon_service.py` provides:
- Singleton service for managing all daemon instances
- Auto-start on application startup
- Graceful shutdown on application stop
- Health checking with heartbeat monitoring
- Log and job history queries
- Configuration updates

Key methods:
- `initialize()`: Auto-starts enabled daemons
- `start_daemon()`, `stop_daemon()`, `restart_daemon()`
- `check_daemon_health()`: Returns healthy/unhealthy/stopped daemons
- `get_daemon_logs()`: Query logs with filtering
- `get_daemon_job_history()`: Query job actions

### 5. WebSocket Integration

Extended `backend/app/services/websocket_manager.py` with:
- Daemon-specific subscriptions
- Real-time message types:
  - `daemon_log`: Individual log entries
  - `daemon_status`: Status updates
  - `daemon_job_action`: Job action notifications
  - `daemon_update`: General daemon updates
- Subscribe/unsubscribe commands for specific daemons

### 6. API Endpoints

`backend/app/api/routes/daemons.py` provides:

- `GET /api/daemons` - List all daemons
- `GET /api/daemons/{id}` - Get daemon details
- `POST /api/daemons/{id}/start` - Start daemon
- `POST /api/daemons/{id}/stop` - Stop daemon
- `POST /api/daemons/{id}/restart` - Restart daemon
- `PUT /api/daemons/{id}` - Update configuration
- `GET /api/daemons/{id}/logs` - Get logs (with filtering)
- `GET /api/daemons/{id}/history` - Get job history
- `GET /api/daemons/health/check` - Check all daemon health
- `WS /api/daemons/ws` - WebSocket for real-time updates

### 7. Application Integration

- Daemon service initialized in `app/main.py` startup
- Graceful shutdown in lifespan manager
- Models registered in `app/models/__init__.py`
- Routes registered in `app/api/__init__.py`

## Frontend Implementation

### 1. Type Definitions

`frontend/src/types/daemon.ts`:
- Complete TypeScript interfaces for all daemon entities
- Enums matching backend
- WebSocket message type union

### 2. Daemon Service

`frontend/src/services/daemonService.ts`:
- Full API client for all daemon endpoints
- Typed request/response handling

### 3. UI Components

#### Daemons List Page (`frontend/src/pages/daemons/Daemons.tsx`)
Features:
- Card-based layout showing all daemons
- Real-time status updates via WebSocket
- Quick actions: Start/Stop/Restart
- Auto-start toggle switch
- Health status indicators
- Uptime display
- Navigation to detail view

#### Daemon Detail Page (`frontend/src/pages/daemons/DaemonDetail.tsx`)
Three tabs:

1. **Logs Tab**:
   - Real-time log streaming via WebSocket
   - Log level filtering (ALL/DEBUG/INFO/WARNING/ERROR)
   - Auto-scroll toggle
   - Pause/resume functionality
   - Clear logs button
   - Export logs to text file
   - Terminal-style display with color coding

2. **Configuration Tab**:
   - JSON editor for daemon configuration
   - Validation before saving
   - Note about restart requirement

3. **Job History Tab**:
   - Table of all job actions
   - Shows time, action, job ID, and reason
   - Chronological order

### 4. Navigation

- Added to router in `frontend/src/router/index.tsx`
- Menu item in sidebar with ThunderboltOutlined icon
- Routes: `/daemons` and `/daemons/:daemonId`

## Key Design Decisions

### 1. Greenlet Error Prevention
- Every database operation uses its own AsyncSession
- No session reuse between contexts
- Progress callbacks create their own sessions
- Clear session boundaries in all operations

### 2. Real-time Updates
- WebSocket for instant log streaming
- Daemon status broadcast to all clients
- Job action notifications
- Subscription model for specific daemons

### 3. Health Monitoring
- Heartbeat mechanism (configurable interval)
- Automatic health status calculation
- Visual indicators in UI

### 4. Configuration Management
- JSONB storage for flexibility
- Runtime configuration updates
- Sensible defaults for all options

### 5. Error Handling
- Daemons continue running on errors
- Errors logged but don't crash daemon
- Graceful shutdown on stop
- Error status for fatal issues

## Usage Guide

### Starting a Daemon
1. Navigate to `/daemons` in UI
2. Click play button on daemon card
3. Daemon starts and status updates to RUNNING

### Monitoring Logs
1. Click settings icon to view details
2. Logs stream in real-time
3. Use filters and controls as needed

### Configuration
1. Go to Configuration tab in detail view
2. Edit JSON configuration
3. Click Update (requires restart)

### Auto-start
- Toggle switch on daemon card
- Daemon will start automatically on system startup

## Test Daemon Features

The TestDaemon demonstrates all capabilities:
- Logs every 5 seconds (configurable)
- Launches test jobs every 30 seconds
- Updates heartbeat every 10 seconds
- Reports memory usage
- Can simulate errors for testing
- Monitors launched jobs until completion

## Future Enhancements

1. **MetadataGenerateWatcher** - First production daemon
2. **Daemon templates** - Quick creation of common daemon types
3. **Performance metrics** - CPU/memory graphs
4. **Alert system** - Notifications for daemon issues
5. **Daemon dependencies** - Start order and dependencies
6. **Resource limits** - CPU/memory constraints

## Troubleshooting

### Daemon Won't Start
- Check logs for errors
- Verify configuration is valid JSON
- Ensure no other instance running

### No Logs Appearing
- Check WebSocket connection
- Verify daemon is actually running
- Check log level filter

### Greenlet Errors
- Review all database operations
- Ensure dedicated sessions used
- Check for session leaks

## Migration Notes

Two Alembic migrations created:
1. `a8bae0a82f5f_add_daemons_tables.py` - Schema creation
2. `d3a21e0e6edd_add_test_daemon_record.py` - Test daemon data

Run migrations with: `alembic upgrade head`

## API Changes

No breaking changes to existing APIs. New endpoints added under `/api/daemons/*`.

## Dependencies

- Backend: psutil (already in requirements.txt)
- Frontend: No new dependencies

## Security Considerations

- Daemons run with application privileges
- Configuration validation prevents injection
- WebSocket authentication inherited from app
- Job actions tracked for audit trail