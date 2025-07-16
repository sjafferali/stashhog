# StashHog Data Models

## Scene Model

The Scene model represents a video file synced from a Stash server. It contains metadata about the video file, relationships to other entities, and tracking information for synchronization.

### Fields

#### Identification
- `id` (String, Primary Key): Unique identifier from Stash

#### Basic Information
- `title` (String, Required): Scene title
- `details` (Text, Optional): Scene description/details
- `url` (String, Optional): Associated URL
- `rating` (Integer, Optional): Rating value (0-5)
- `organized` (Boolean, Default: False): Whether the scene is organized in Stash
- `analyzed` (Boolean, Default: False): Whether the scene has been analyzed by StashHog

#### File Information
- `paths` (JSON Array): List of file paths associated with the scene
- `duration` (Float, Optional): Video duration in seconds
- `size` (Integer, Optional): File size in bytes
- `width` (Integer, Optional): Video width in pixels
- `height` (Integer, Optional): Video height in pixels
- `framerate` (Float, Optional): Video frame rate (fps)
- `bitrate` (Integer, Optional): Video bitrate in kbps
- `codec` (String, Optional): Video codec name

#### Timestamps

##### StashHog Internal (from BaseModel)
- `created_at` (DateTime): When the record was created in StashHog database
- `updated_at` (DateTime): When the record was last modified in StashHog database

##### Stash Source Data
- `stash_created_at` (DateTime, Required): When the scene was created in Stash
- `stash_updated_at` (DateTime, Optional): When the scene was last updated in Stash
- `stash_date` (DateTime, Optional): The actual date of the scene content (when filmed)

##### Sync Tracking
- `last_synced` (DateTime, Required): When StashHog last synced this scene from Stash
- `content_checksum` (String, Optional): Checksum for detecting content changes

#### Relationships
- `studio` (Many-to-One): The studio that produced the scene
- `performers` (Many-to-Many): Performers in the scene
- `tags` (Many-to-Many): Tags associated with the scene
- `plan_changes` (One-to-Many): Analysis plan changes for this scene

### Indexes
- Primary key index on `id`
- Composite indexes for common query patterns:
  - `idx_scene_organized_date`: (organized, stash_date)
  - `idx_scene_studio_date`: (studio_id, stash_date)
  - `idx_scene_sync_status`: (last_synced, organized)
  - `idx_scene_analyzed`: (analyzed)
  - `idx_scene_analyzed_organized`: (analyzed, organized)

### Usage Notes

1. **Date Field Naming Convention**: All fields that come from Stash are prefixed with `stash_` to clearly distinguish them from StashHog's internal tracking fields.

2. **Sync Strategy**: The `stash_updated_at` field is used by the incremental sync strategy to determine if a scene needs to be updated.

3. **File Paths**: The `paths` field stores an array of file paths as some scenes may have multiple files (different qualities, formats, etc.).

4. **Nullable Fields**: Most metadata fields are nullable as they may not be available for all scenes or may not be extracted successfully.

## Performer Model

The Performer model represents an adult performer.

### Fields

#### Identification
- `id` (String, Primary Key): Unique identifier from Stash
- `name` (String, Required): Performer name
- `aliases` (JSON Array, Optional): Alternative names

#### Personal Information
- `gender` (String, Optional): Gender
- `birthdate` (Date, Optional): Date of birth
- `country` (String, Optional): Country of origin
- `ethnicity` (String, Optional): Ethnicity
- `hair_color` (String, Optional): Hair color
- `eye_color` (String, Optional): Eye color

#### Physical Attributes
- `height_cm` (Integer, Optional): Height in centimeters
- `weight_kg` (Integer, Optional): Weight in kilograms
- `measurements` (String, Optional): Body measurements
- `fake_tits` (Boolean, Optional): Whether breast implants
- `tattoos` (Text, Optional): Tattoo descriptions
- `piercings` (Text, Optional): Piercing descriptions

#### Career Information
- `career_length` (String, Optional): Career duration
- `url` (String, Optional): Official website
- `twitter` (String, Optional): Twitter handle
- `instagram` (String, Optional): Instagram handle

#### Additional Fields
- `details` (Text, Optional): Additional details/biography
- `rating` (Integer, Optional): Rating value
- `favorite` (Boolean, Default: False): Marked as favorite
- `ignore_auto_tag` (Boolean, Default: False): Ignore in auto-tagging
- `image_url` (String, Optional): Profile image URL

#### Relationships
- `scenes` (Many-to-Many): Scenes featuring this performer

## Tag Model

The Tag model represents content tags/categories.

### Fields

#### Identification
- `id` (String, Primary Key): Unique identifier from Stash
- `name` (String, Required): Tag name
- `aliases` (JSON Array, Optional): Alternative names

#### Additional Information
- `description` (Text, Optional): Tag description
- `ignore_auto_tag` (Boolean, Default: False): Ignore in auto-tagging

#### Hierarchy
- `parent_id` (String, Optional): Parent tag ID
- `parent` (Many-to-One): Parent tag relationship
- `children` (One-to-Many): Child tags

#### Relationships
- `scenes` (Many-to-Many): Scenes with this tag

## Studio Model

The Studio model represents production studios.

### Fields

#### Identification
- `id` (String, Primary Key): Unique identifier from Stash
- `name` (String, Required): Studio name
- `aliases` (JSON Array, Optional): Alternative names

#### Additional Information
- `url` (String, Optional): Official website
- `details` (Text, Optional): Studio description
- `rating` (Integer, Optional): Rating value
- `favorite` (Boolean, Default: False): Marked as favorite
- `ignore_auto_tag` (Boolean, Default: False): Ignore in auto-tagging
- `image_url` (String, Optional): Studio logo URL

#### Hierarchy
- `parent_id` (String, Optional): Parent studio ID
- `parent` (Many-to-One): Parent studio relationship
- `subsidiaries` (One-to-Many): Subsidiary studios

#### Relationships
- `scenes` (One-to-Many): Scenes from this studio

## Database Design Considerations

### Primary Keys
All models use string primary keys to match Stash's ID format. This avoids ID conflicts and simplifies synchronization.

### Timestamps
Each model inherits from BaseModel which provides:
- `created_at`: When the record was created in StashHog
- `updated_at`: When the record was last modified in StashHog
- `last_synced`: When the record was last synced from Stash

### JSON Fields
Several fields use JSON type for flexible data storage:
- `aliases`: Store multiple alternative names
- `paths`: Store multiple file paths for scenes
- `error_details`: Store structured error information

### Indexes
Strategic indexes are created for:
- Foreign key relationships
- Common query patterns (e.g., organized scenes by date)
- Sync status tracking

### Soft Relationships
Some relationships use "temp" IDs during initial sync and are resolved in a second pass. This handles circular dependencies in the Stash data model.