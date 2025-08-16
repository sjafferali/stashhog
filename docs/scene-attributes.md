# Scene Attributes Documentation

## Overview

StashHog uses three primary attributes to track the processing state of scenes:
- **`analyzed`**: Indicates whether a scene has undergone AI or non-AI metadata analysis (performers, studios, tags, details)
- **`video_analyzed`**: Indicates whether a scene has undergone video tag analysis (frame-by-frame video content analysis)
- **`generated`**: Indicates whether a scene's metadata has been generated or processed through automated workflows

These attributes are essential for workflow automation, filtering, and tracking which scenes have been processed.

## Attribute Usage Patterns

### The `generated` Attribute
The `generated` attribute is designed for tracking scenes whose metadata has been artificially generated or processed through automated workflows. Common use cases include:

- **AI-Generated Content**: Scenes with metadata created by AI systems
- **Automated Processing**: Scenes processed through batch operations or scheduled workflows  
- **Synthetic Metadata**: Scenes with artificially created tags, descriptions, or classifications
- **Workflow Tracking**: Marking scenes that have completed specific automated processing pipelines
- **Quality Control**: Distinguishing between manually curated and automatically generated metadata

Unlike `analyzed` (which tracks metadata analysis) and `video_analyzed` (which tracks video content analysis), `generated` focuses on the origin and nature of the scene's metadata - specifically whether it was created through automated generation processes.

## Database Schema

### Model Definition
Location: `backend/app/models/scene.py`

```python
class Scene(BaseModel):
    # ...
    analyzed = Column(Boolean, default=False, nullable=False, index=True)
    video_analyzed = Column(Boolean, default=False, nullable=False, index=True)
    generated = Column(Boolean, default=False, nullable=False, index=True)
    # ...
```

### Database Indexes
- `idx_scene_analyzed`: Index on `analyzed` column for fast filtering
- `idx_scene_analyzed_organized`: Composite index on `(analyzed, organized)` for common queries
- `ix_scene_video_analyzed`: Index on `video_analyzed` column for fast filtering
- `ix_scene_generated`: Index on `generated` column for fast filtering
- `idx_scene_generated_organized`: Composite index on `(generated, organized)` for common queries

### Migrations
- **`analyzed` field**: Added in migration `005_add_analyzed_field_to_scene.py` (2025-01-16)
- **`video_analyzed` field**: Added in migration `6b8cfe198609_add_video_analyzed_column_to_scenes_.py` (2025-07-18)
- **`generated` field**: Added in migration `add_generated_column_to_scenes.py` (2025-08-16)

## Backend Implementation

### 1. API Endpoints

#### Bulk Update Endpoint
**Location**: `backend/app/api/routes/scenes.py:598-630`
- **Endpoint**: `PATCH /scenes/bulk-update`
- **Purpose**: Allows bulk updating of `analyzed`, `video_analyzed`, and `generated` attributes
- **Allowed fields**: Only `analyzed`, `video_analyzed`, and `generated` can be updated through this endpoint
- **Usage**: Updates multiple scenes with the same attribute values

```python
# Example request body
{
    "scene_ids": ["scene1", "scene2", "scene3"],
    "updates": {
        "analyzed": true,
        "video_analyzed": false,
        "generated": true
    }
}
```

#### Scene Filtering
**Location**: `backend/app/api/routes/scenes.py:56-100`
- All three attributes can be used as query parameters for filtering scenes
- Parameters: `analyzed` (boolean), `video_analyzed` (boolean), `generated` (boolean)
- Example: `GET /scenes?analyzed=false&video_analyzed=true&generated=false`

### 2. Automatic Attribute Setting

#### During Analysis Jobs
**Location**: `backend/app/services/analysis/analysis_service.py`

##### When `analyzed` is set to `true`:
- After successful AI analysis with any of these options:
  - `detect_performers`
  - `detect_studios`
  - `detect_tags`
  - `detect_details`
- Set in `_mark_scenes_as_analyzed()` method (lines 1145-1148)
- Updated when analysis plan changes are applied (lines 2073-2079)

##### When `video_analyzed` is set to `true`:
- After successful video tag detection (`detect_video_tags` option)
- Set in `_mark_scenes_as_analyzed()` method (lines 1150-1151)
- Updated when video analysis is completed (lines 2068-2071)

#### Auto Video Analysis Daemon
**Location**: `backend/app/daemons/auto_video_analysis_daemon.py`
- **Purpose**: Automatically analyzes scenes without video analysis
- **Process**:
  1. Checks for scenes where `video_analyzed=False` (line 117)
  2. Creates video tag analysis jobs in batches
  3. Monitors job completion
  4. Automatically approves and applies generated plans
  5. This sets `video_analyzed=True` upon completion

#### Process New Scenes Job
**Location**: `backend/app/jobs/process_new_scenes_job.py`
- Part of the workflow that processes newly downloaded scenes
- Can trigger analysis which sets these attributes

### 3. Service Layer

#### Scene Service
**Location**: `backend/app/services/scene_service.py`
- Handles scene updates including attribute modifications
- Used by sync services and analysis services

#### Analysis Service
**Location**: `backend/app/services/analysis/analysis_service.py`
- Main service responsible for analyzing scenes
- Sets attributes based on analysis type:
  - Regular analysis (AI/non-AI) → sets `analyzed`
  - Video tag analysis → sets `video_analyzed`

## Frontend Implementation

### 1. UI Components

#### Scene Actions Component
**Location**: `frontend/src/pages/scenes/components/SceneActions.tsx`

##### Bulk Operations Menu (lines 388-461)
Provides UI actions for bulk attribute updates:
- **Set Analyzed**: Marks selected scenes as `analyzed=true`
- **Unset Analyzed**: Marks selected scenes as `analyzed=false`
- **Set Video Analyzed**: Marks selected scenes as `video_analyzed=true`
- **Unset Video Analyzed**: Marks selected scenes as `video_analyzed=false`
- **Set Generated**: Marks selected scenes as `generated=true`
- **Unset Generated**: Marks selected scenes as `generated=false`

##### Bulk Update Mutation (lines 194-230)
- Handles the API call to update scene attributes
- Shows success message with count of updated scenes
- Invalidates scene queries to refresh the UI

#### Advanced Filters Component
**Location**: `frontend/src/pages/scenes/components/AdvancedFilters.tsx`

##### Status Filter Panel (lines 432-560)
Provides filter controls for:
- **Analyzed Status**: Dropdown with options "Yes", "No", or "Any"
- **Video Analyzed Status**: Dropdown with options "Yes", "No", or "Any"
- **Generated Status**: Dropdown with options "Yes", "No", or "Any"
- Shows count badge when filters are active

### 2. Display Components

#### Scene List/Grid Views
**Location**: `frontend/src/pages/scenes/components/ListView.tsx`, `GridView.tsx`
- Display attribute status as visual indicators
- Icons or badges show whether a scene is analyzed/video_analyzed/generated
- Uses distinct colors and icons for each attribute:
  - `analyzed`: Green CheckCircleOutlined
  - `video_analyzed`: Purple VideoCameraOutlined  
  - `generated`: Blue RobotOutlined

#### Scene Detail Modal
**Location**: `frontend/src/pages/scenes/components/SceneDetailModal.tsx`
- Shows current status of all three attributes
- Allows individual scene attribute updates with toggle buttons
- Provides mutations for updating each attribute independently

### 3. Type Definitions
**Location**: `frontend/src/types/models.ts`
```typescript
interface Scene {
  // ...
  analyzed: boolean;
  video_analyzed: boolean;
  generated: boolean;
  // ...
}
```

## Usage Workflows

### 1. Manual Workflow
1. User selects scenes in the UI
2. Uses bulk actions menu to:
   - Trigger analysis (sets attributes automatically on completion)
   - Manually set/unset attributes
3. Filters scenes by attribute status to track progress

### 2. Automated Workflow
1. **Auto Video Analysis Daemon** continuously:
   - Finds scenes with `video_analyzed=false`
   - Creates analysis jobs
   - Sets `video_analyzed=true` on completion
2. **Process New Scenes Job** workflow:
   - Downloads new content
   - Runs Stash scan
   - Syncs to database
   - Triggers analysis (sets attributes)
   - Generates Stash metadata

### 3. Analysis Job Workflow
1. User or daemon creates analysis job
2. Analysis service processes scenes
3. Based on analysis options:
   - Metadata analysis → sets `analyzed=true`
   - Video tag analysis → sets `video_analyzed=true`
4. Attributes updated in database after successful completion

## Dashboard Integration

### Dashboard Status Service
**Location**: `backend/app/services/dashboard_status_service.py`
- Provides statistics on analyzed/video_analyzed scenes
- Used for dashboard metrics and progress tracking

## Testing

### Backend Tests
- `backend/tests/test_api_routes_scenes.py`: Tests bulk update endpoint
- `backend/tests/models/test_model_scene.py`: Tests model attributes
- `backend/tests/test_scene_service.py`: Tests service layer updates

### Frontend Tests
- `frontend/src/pages/scenes/components/SceneActions.test.tsx`: Tests bulk actions
- `frontend/src/pages/Dashboard.test.tsx`: Tests dashboard display

---

## Adding New Scene Attributes

To add a new boolean attribute similar to `analyzed` or `video_analyzed`, follow these steps:

### 1. Database Migration
Create a new Alembic migration:
```bash
cd backend
alembic revision -m "Add new_attribute to scene table"
```

Edit the migration file:
```python
def upgrade():
    op.add_column(
        "scene",
        sa.Column("new_attribute", sa.Boolean(), nullable=False, server_default="false")
    )
    op.create_index("idx_scene_new_attribute", "scene", ["new_attribute"])

def downgrade():
    op.drop_index("idx_scene_new_attribute", table_name="scene")
    op.drop_column("scene", "new_attribute")
```

### 2. Update Backend Model
**File**: `backend/app/models/scene.py`
```python
class Scene(BaseModel):
    # ...
    new_attribute = Column(Boolean, default=False, nullable=False, index=True)
    # ...
```

### 3. Update API Schema
**File**: `backend/app/api/schemas/__init__.py`
Add to `SceneResponse` and `SceneFilter`:
```python
class SceneResponse(BaseModel):
    # ...
    new_attribute: bool
    
class SceneFilter(BaseModel):
    # ...
    new_attribute: Optional[bool] = None
```

### 4. Update API Routes
**File**: `backend/app/api/routes/scenes.py`

a. Add to query parameters in `parse_scene_filters()`:
```python
new_attribute: Optional[bool] = Query(None),
```

b. Add to allowed fields in `bulk_update_scenes()`:
```python
allowed_fields = {"analyzed", "video_analyzed", "generated", "new_attribute"}
```

c. Add to filter conditions in `_apply_boolean_filters()`:
```python
if filters.new_attribute is not None:
    conditions.append(Scene.new_attribute == filters.new_attribute)
```

### 5. Update Frontend Types
**File**: `frontend/src/types/models.ts`
```typescript
export interface Scene {
  // ...
  new_attribute: boolean;
}
```

### 6. Update Frontend Filters
**File**: `frontend/src/pages/scenes/components/AdvancedFilters.tsx`
Add a new filter control similar to analyzed/video_analyzed

### 7. Update Frontend Actions
**File**: `frontend/src/pages/scenes/components/SceneActions.tsx`
Add menu items for setting/unsetting the new attribute:
```typescript
{
  key: 'set-new-attribute',
  label: 'Set New Attribute',
  icon: <CheckCircleOutlined />,
},
{
  key: 'unset-new-attribute',
  label: 'Unset New Attribute',
  icon: <CloseCircleOutlined />,
}
```

### 8. Update Service Logic
Determine where and when the attribute should be set:
- Add to analysis service if set during analysis
- Create a daemon if it needs automatic processing
- Add to sync service if it comes from external source

### 9. Add Tests
- Backend: Test model, API endpoints, and service logic
- Frontend: Test filter controls and bulk actions

### 10. Update Documentation
- Add the new attribute to this documentation file
- Update API documentation
- Add any workflow-specific documentation

## Best Practices

1. **Attribute Naming**: Use descriptive boolean names that clearly indicate state (e.g., `is_processed`, `has_preview`, `needs_review`)

2. **Default Values**: Always provide sensible defaults (usually `False` for boolean attributes)

3. **Indexing**: Create indexes for attributes that will be frequently filtered

4. **Bulk Operations**: Always provide bulk update capabilities for boolean attributes

5. **UI Feedback**: Show clear visual indicators of attribute state in the UI

6. **Automation**: Consider if the attribute should be automatically set/unset by daemons or jobs

7. **Testing**: Ensure comprehensive test coverage for all attribute operations

8. **Migration Safety**: Use batch updates in migrations to avoid timeouts on large databases