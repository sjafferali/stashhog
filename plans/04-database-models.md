# Task 04: Database Models and Migrations

## Current State
- Backend structure is in place with routes and configuration
- No database models defined
- No migration system configured
- SQLite database URL configured in settings

## Objective
Implement SQLAlchemy models for all entities, configure Alembic for migrations, and create the initial database schema.

## Requirements

### Database Configuration

1. **app/core/database.py** - Database setup:
   ```python
   # Components to implement:
   - SQLAlchemy engine configuration
   - Session factory with proper settings
   - Base declarative class
   - get_db dependency for FastAPI
   - Database initialization function
   ```

### Base Model

2. **app/models/base.py** - Base model class:
   ```python
   # Base model with common fields:
   - id (UUID or Integer based on entity)
   - created_at (timestamp)
   - updated_at (timestamp)
   - Automatic timestamp updates
   - to_dict() method for serialization
   ```

### Entity Models

3. **app/models/scene.py** - Scene model:
   ```python
   # Fields:
   - id: String (primary key from Stash)
   - title: String
   - paths: JSON (list of file paths)
   - organized: Boolean
   - details: Text (nullable)
   - created_date: DateTime
   - scene_date: DateTime (nullable)
   - studio_id: String (foreign key, nullable)
   - last_synced: DateTime
   
   # Relationships:
   - studio: Many-to-One
   - performers: Many-to-Many
   - tags: Many-to-Many
   - plan_changes: One-to-Many
   ```

4. **app/models/performer.py** - Performer model:
   ```python
   # Fields:
   - id: String (primary key from Stash)
   - name: String (indexed)
   - last_synced: DateTime
   
   # Relationships:
   - scenes: Many-to-Many
   ```

5. **app/models/tag.py** - Tag model:
   ```python
   # Fields:
   - id: String (primary key from Stash)
   - name: String (indexed, unique)
   - last_synced: DateTime
   
   # Relationships:
   - scenes: Many-to-Many
   ```

6. **app/models/studio.py** - Studio model:
   ```python
   # Fields:
   - id: String (primary key from Stash)
   - name: String (indexed)
   - last_synced: DateTime
   
   # Relationships:
   - scenes: One-to-Many
   ```

### Association Tables

7. **app/models/associations.py** - Many-to-Many tables:
   ```python
   # Tables:
   - scene_performers (scene_id, performer_id)
   - scene_tags (scene_id, tag_id)
   # Both with composite primary keys
   ```

### Analysis Models

8. **app/models/analysis_plan.py** - Analysis plan model:
   ```python
   # Fields:
   - id: Integer (auto-increment primary key)
   - name: String
   - description: Text (nullable)
   - metadata: JSON (settings used, stats)
   - status: Enum (draft, reviewing, applied, cancelled)
   - created_at: DateTime
   - applied_at: DateTime (nullable)
   
   # Relationships:
   - changes: One-to-Many with PlanChange
   ```

9. **app/models/plan_change.py** - Individual changes:
   ```python
   # Fields:
   - id: Integer (auto-increment primary key)
   - plan_id: Integer (foreign key)
   - scene_id: String (foreign key)
   - field: String (performer, tag, studio, details, etc.)
   - action: Enum (add, remove, update, set)
   - current_value: JSON
   - proposed_value: JSON
   - confidence: Float (nullable, 0-1)
   - applied: Boolean (default False)
   - applied_at: DateTime (nullable)
   
   # Relationships:
   - plan: Many-to-One
   - scene: Many-to-One
   ```

### Job Tracking

10. **app/models/job.py** - Background job model:
    ```python
    # Fields:
    - id: String (UUID primary key)
    - type: String (sync, analysis, apply_plan)
    - status: Enum (pending, running, completed, failed, cancelled)
    - progress: Integer (0-100)
    - total_items: Integer (nullable)
    - processed_items: Integer (default 0)
    - result: JSON (nullable)
    - error: Text (nullable)
    - created_at: DateTime
    - started_at: DateTime (nullable)
    - completed_at: DateTime (nullable)
    
    # Methods:
    - update_progress()
    - mark_completed()
    - mark_failed()
    ```

### Settings and Scheduling

11. **app/models/setting.py** - Application settings:
    ```python
    # Fields:
    - key: String (primary key)
    - value: JSON
    - description: String (nullable)
    - updated_at: DateTime
    ```

12. **app/models/scheduled_task.py** - Scheduled tasks:
    ```python
    # Fields:
    - id: Integer (auto-increment primary key)
    - name: String (unique)
    - task_type: String (sync, analysis)
    - schedule: String (cron expression)
    - config: JSON (task-specific config)
    - enabled: Boolean (default True)
    - last_run: DateTime (nullable)
    - next_run: DateTime (nullable)
    - last_job_id: String (nullable)
    ```

### Model Initialization

13. **app/models/__init__.py** - Export all models:
    ```python
    # Import and export all models
    # This ensures they're registered with SQLAlchemy
    ```

### Alembic Setup

14. **alembic.ini** - Alembic configuration:
    - Configure database URL from environment
    - Set up migration directories
    - Configure logging

15. **alembic/env.py** - Migration environment:
    - Import all models
    - Configure metadata
    - Handle async database operations

16. **Initial migration** - Create all tables:
    ```bash
    alembic init alembic
    alembic revision --autogenerate -m "Initial schema"
    ```

### Database Utilities

17. **app/core/db_utils.py** - Database helpers:
    ```python
    # Utilities:
    - init_db() - Create tables if not exist
    - drop_db() - Drop all tables (dev only)
    - seed_db() - Add initial data
    - check_db_health() - Verify connection
    ```

## Expected Outcome

After completing this task:
- All database models are defined with proper relationships
- Alembic is configured for migrations
- Initial migration creates all tables
- Database can be initialized and seeded
- Models support all required operations

## Integration Points
- Models integrate with SQLAlchemy ORM
- Migrations managed by Alembic
- Database sessions managed by FastAPI
- Models used by services and routes

## Success Criteria
1. All models import without errors
2. `alembic upgrade head` creates all tables
3. Relationships work correctly
4. Timestamps update automatically
5. JSON fields serialize/deserialize properly
6. Indexes are created for performance
7. Foreign key constraints are enforced
8. Models have proper type hints
9. Database health check passes