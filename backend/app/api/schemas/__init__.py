"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Generic type for paginated responses
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={"example": {}},
    )


# Pagination schemas
class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(50, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Literal["asc", "desc"] = Field("asc", description="Sort order")


# Common response schemas
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")


class VersionResponse(BaseModel):
    """Version information response."""

    name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment")
    debug: bool = Field(..., description="Debug mode")
    features: Optional[dict[str, bool]] = Field(None, description="Enabled features")


class ErrorDetail(BaseModel):
    """Error detail information."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = Field(False, description="Success status")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "Resource not found",
                "detail": "Scene with ID 123 not found",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = Field(True, description="Success status")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[dict[str, Any]] = Field(None, description="Additional data")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, per_page: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(items=items, total=total, page=page, per_page=per_page, pages=pages)


# Job-related schemas
class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CANCELLING = "cancelling"


class JobType(str, Enum):
    """Job type enumeration."""

    SCENE_SYNC = "scene_sync"
    SCENE_ANALYSIS = "scene_analysis"
    SETTINGS_TEST = "settings_test"
    SYNC = "sync"
    SYNC_SCENES = "sync_scenes"
    ANALYSIS = "analysis"
    NON_AI_ANALYSIS = "non_ai_analysis"
    APPLY_PLAN = "apply_plan"
    VIDEO_TAG_ANALYSIS = "video_tag_analysis"
    GENERATE_DETAILS = "generate_details"
    EXPORT = "export"
    IMPORT = "import"
    CLEANUP = "cleanup"
    REMOVE_ORPHANED_ENTITIES = "remove_orphaned_entities"
    PROCESS_DOWNLOADS = "process_downloads"
    STASH_SCAN = "stash_scan"
    STASH_GENERATE = "stash_generate"
    CHECK_STASH_GENERATE = "check_stash_generate"
    PROCESS_NEW_SCENES = "process_new_scenes"
    TEST = "test"


class JobCreate(BaseSchema):
    """Schema for creating a job."""

    type: JobType = Field(..., description="Job type")
    parameters: Optional[dict[str, Any]] = Field(
        default_factory=lambda: {}, description="Job parameters"
    )


class JobUpdate(BaseSchema):
    """Schema for updating a job."""

    status: Optional[JobStatus] = Field(None, description="Job status")
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    result: Optional[dict[str, Any]] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message")


class JobResponse(BaseSchema):
    """Job response schema."""

    id: str = Field(..., description="Job ID")
    type: JobType = Field(..., description="Job type")
    status: JobStatus = Field(..., description="Job status")
    progress: float = Field(0, description="Progress percentage")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Job parameters"
    )
    metadata: Optional[dict[str, Any]] = Field(None, description="Job metadata")
    result: Optional[dict[str, Any]] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    total: Optional[int] = Field(None, description="Total items to process")
    processed_items: Optional[int] = Field(
        None, description="Number of items processed"
    )


class JobDetailResponse(JobResponse):
    """Detailed job response with additional information."""

    logs: Optional[list[str]] = Field(None, description="Job logs")


class JobsListResponse(BaseSchema):
    """Response wrapper for jobs list endpoint."""

    jobs: list[JobResponse] = Field(..., description="List of jobs")


# Entity schemas
class PerformerResponse(BaseSchema):
    """Performer response schema."""

    id: str = Field(..., description="Performer ID")
    name: str = Field(..., description="Performer name")
    scene_count: Optional[int] = Field(None, description="Number of scenes")
    gender: Optional[str] = Field(None, description="Performer gender")
    favorite: bool = Field(False, description="Is favorite")
    rating100: Optional[int] = Field(None, description="Rating out of 100")


class TagResponse(BaseSchema):
    """Tag response schema."""

    id: str = Field(..., description="Tag ID")
    name: str = Field(..., description="Tag name")
    scene_count: Optional[int] = Field(None, description="Number of scenes")


class StudioResponse(BaseSchema):
    """Studio response schema."""

    id: str = Field(..., description="Studio ID")
    name: str = Field(..., description="Studio name")
    scene_count: Optional[int] = Field(None, description="Number of scenes")


# Scene-related schemas
# Scene Marker schemas
class SceneMarkerResponse(BaseSchema):
    """Scene marker response schema."""

    id: str = Field(..., description="Marker ID")
    title: str = Field(..., description="Marker title")
    seconds: float = Field(..., description="Start time in seconds")
    end_seconds: Optional[float] = Field(None, description="End time in seconds")
    primary_tag: TagResponse = Field(..., description="Primary tag")
    tags: list[TagResponse] = Field(default_factory=list, description="Additional tags")
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated timestamp")


# Scene File schema
class SceneFileResponse(BaseSchema):
    """Scene file response schema."""

    id: str = Field(..., description="File ID")
    path: str = Field(..., description="File path")
    basename: Optional[str] = Field(None, description="File basename")
    is_primary: bool = Field(..., description="Is primary file")
    size: Optional[int] = Field(None, description="File size in bytes")
    format: Optional[str] = Field(None, description="File format")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    width: Optional[int] = Field(None, description="Video width")
    height: Optional[int] = Field(None, description="Video height")
    video_codec: Optional[str] = Field(None, description="Video codec")
    audio_codec: Optional[str] = Field(None, description="Audio codec")
    frame_rate: Optional[float] = Field(None, description="Frame rate")
    bit_rate: Optional[int] = Field(None, description="Bitrate in bps")
    oshash: Optional[str] = Field(None, description="OSHash fingerprint")
    phash: Optional[str] = Field(None, description="PHash fingerprint")
    mod_time: Optional[datetime] = Field(None, description="File modification time")


# Scene-related schemas
class SceneBase(BaseSchema):
    """Base scene schema."""

    id: str = Field(..., description="Scene ID")
    title: str = Field(..., description="Scene title")
    paths: list[str] = Field(..., description="API URLs for media")
    file_path: Optional[str] = Field(None, description="Actual file path")
    organized: bool = Field(..., description="Is scene organized")
    analyzed: bool = Field(..., description="Is scene analyzed")
    video_analyzed: bool = Field(False, description="Has video tag analysis been run")
    details: Optional[str] = Field(None, description="Scene details/description")
    stash_created_at: datetime = Field(
        ..., description="When scene was created in Stash"
    )
    stash_updated_at: Optional[datetime] = Field(
        None, description="When scene was last updated in Stash"
    )
    stash_date: Optional[datetime] = Field(
        None, description="Actual scene date (when filmed)"
    )


class SceneCreate(SceneBase):
    """Schema for creating a scene."""

    pass


class SceneUpdate(SceneBase):
    """Schema for updating a scene."""

    tags: Optional[list[str]] = Field(None, description="Scene tags")
    performers: Optional[list[str]] = Field(None, description="Scene performers")
    studio: Optional[str] = Field(None, description="Studio name")


class JobInfo(BaseSchema):
    """Minimal job information for scene display."""

    id: str = Field(..., description="Job ID")
    type: JobType = Field(..., description="Job type")
    status: JobStatus = Field(..., description="Job status")
    progress: int = Field(..., description="Progress percentage")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")


class SceneResponse(SceneBase):
    """Scene response schema."""

    studio: Optional[StudioResponse] = Field(None, description="Studio")
    performers: list[PerformerResponse] = Field(
        default_factory=list, description="Scene performers"
    )
    tags: list[TagResponse] = Field(default_factory=list, description="Scene tags")
    markers: list[SceneMarkerResponse] = Field(
        default_factory=list, description="Scene markers"
    )
    files: list[SceneFileResponse] = Field(
        default_factory=list, description="Scene files"
    )
    last_synced: datetime = Field(..., description="Last sync timestamp")
    created_at: datetime = Field(..., description="When scene was created in StashHog")
    updated_at: datetime = Field(
        ..., description="When scene was last updated in StashHog"
    )

    # Metadata fields
    duration: Optional[float] = Field(None, description="Duration in seconds")
    size: Optional[int] = Field(None, description="File size in bytes")
    width: Optional[int] = Field(None, description="Video width")
    height: Optional[int] = Field(None, description="Video height")
    framerate: Optional[float] = Field(None, description="Frame rate")
    bitrate: Optional[int] = Field(None, description="Bitrate in kbps")
    video_codec: Optional[str] = Field(None, description="Video codec")

    # Job-related fields
    active_jobs: list[JobInfo] = Field(
        default_factory=list, description="Currently running jobs for this scene"
    )
    recent_jobs: list[JobInfo] = Field(
        default_factory=list, description="Recently completed jobs (last 24 hours)"
    )


class SceneFilter(BaseSchema):
    """Scene filter parameters."""

    search: Optional[str] = Field(None, description="Search text")
    scene_ids: Optional[list[str]] = Field(None, description="Filter by scene IDs")
    studio_id: Optional[str] = Field(None, description="Filter by studio ID")
    performer_ids: Optional[list[str]] = Field(
        None, description="Filter by performer IDs"
    )
    tag_ids: Optional[list[str]] = Field(None, description="Filter by tag IDs")
    exclude_tag_ids: Optional[list[str]] = Field(
        None, description="Filter by tag IDs to exclude"
    )
    organized: Optional[bool] = Field(None, description="Filter by organized status")
    analyzed: Optional[bool] = Field(None, description="Filter by analyzed status")
    video_analyzed: Optional[bool] = Field(
        None, description="Filter by video analyzed status"
    )
    date_from: Optional[datetime] = Field(None, description="Filter by date from")
    date_to: Optional[datetime] = Field(None, description="Filter by date to")
    has_active_jobs: Optional[bool] = Field(
        None, description="Filter scenes with running/pending jobs"
    )


class SceneSyncRequest(BaseSchema):
    """Request to sync scenes from Stash."""

    filter: Optional[dict[str, Any]] = Field(None, description="Stash filter criteria")
    limit: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum scenes to sync"
    )


# Analysis-related schemas
class AnalysisOptions(BaseSchema):
    """Analysis options schema."""

    detect_performers: bool = Field(True, description="Detect performers")
    detect_studios: bool = Field(True, description="Detect studios")
    detect_tags: bool = Field(True, description="Detect tags")
    detect_details: bool = Field(True, description="Generate/enhance details")
    detect_video_tags: bool = Field(
        False, description="Detect tags/markers from video content"
    )
    confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class AnalysisRequest(BaseSchema):
    """Analysis request schema."""

    scene_ids: Optional[list[str]] = Field(
        None, description="Specific scene IDs to analyze"
    )
    filters: Optional[SceneFilter] = Field(None, description="Scene filters")
    options: AnalysisOptions = Field(
        default_factory=lambda: AnalysisOptions(
            detect_performers=True,
            detect_studios=True,
            detect_tags=True,
            detect_details=True,
            detect_video_tags=False,
            confidence_threshold=0.7,
        ),
        description="Analysis options",
    )
    plan_name: Optional[str] = Field(None, description="Name for the analysis plan")


class ChangePreview(BaseSchema):
    """Preview of a single change."""

    id: Optional[int] = Field(None, description="Change ID")
    field: str = Field(..., description="Field to change")
    action: str = Field(..., description="Action type (add, update, remove)")
    current_value: Any = Field(..., description="Current value")
    proposed_value: Any = Field(..., description="Proposed value")
    confidence: float = Field(..., description="Confidence score")
    status: Optional[str] = Field(
        None, description="Change status (pending, approved, rejected, applied)"
    )
    applied: Optional[bool] = Field(
        None, description="Whether the change has been applied to Stash"
    )


class SceneChanges(BaseSchema):
    """Changes for a single scene."""

    scene_id: str = Field(..., description="Scene ID")
    scene_title: str = Field(..., description="Scene title")
    scene_path: Optional[str] = Field(None, description="Scene file path")
    changes: list[ChangePreview] = Field(..., description="List of changes")


class AnalysisPlanCreate(BaseSchema):
    """Schema for creating an analysis plan."""

    scene_ids: Optional[list[str]] = Field(
        None, description="Specific scene IDs to analyze"
    )
    filters: Optional[dict[str, Any]] = Field(
        None, description="Filters for scene selection"
    )
    detect_performers: bool = Field(True, description="Detect performers")
    detect_studios: bool = Field(True, description="Detect studios")
    detect_tags: bool = Field(True, description="Detect tags")
    detect_details: bool = Field(True, description="Generate/enhance details")
    confidence_threshold: float = Field(0.7, description="Minimum confidence threshold")


class PlanResponse(BaseSchema):
    """Analysis plan response schema."""

    id: int = Field(..., description="Plan ID")
    name: str = Field(..., description="Plan name")
    status: str = Field(..., description="Plan status")
    created_at: datetime = Field(..., description="Creation timestamp")
    total_scenes: int = Field(..., description="Total scenes analyzed")
    total_changes: int = Field(..., description="Total proposed changes")
    approved_changes: int = Field(0, description="Total approved changes")
    rejected_changes: int = Field(0, description="Total rejected changes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Plan metadata")
    job_id: Optional[str] = Field(None, description="Job ID that created this plan")


class PlanDetailResponse(PlanResponse):
    """Detailed analysis plan response with changes."""

    scenes: list[SceneChanges] = Field(..., description="Changes grouped by scene")


class AnalysisApplyRequest(BaseSchema):
    """Request to apply an analysis plan."""

    apply_tags: bool = Field(True, description="Apply suggested tags")
    apply_performers: bool = Field(True, description="Apply suggested performers")
    apply_details: bool = Field(True, description="Apply suggested details")
    custom_modifications: Optional[dict[str, Any]] = Field(
        None, description="Custom modifications"
    )


class ApplyPlanRequest(BaseSchema):
    """Request to apply plan changes."""

    change_ids: Optional[list[int]] = Field(
        None,
        description="Specific change IDs to apply. If not provided, all non-rejected changes will be applied.",
    )
    background: bool = Field(True, description="Run as background job")


# Settings-related schemas
class SettingsUpdate(BaseSchema):
    """Schema for updating settings."""

    stash_url: Optional[str] = Field(None, description="Stash server URL")
    stash_api_key: Optional[str] = Field(None, description="Stash API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: Optional[str] = Field(None, description="OpenAI model")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"stash_url": "http://localhost:9999", "openai_model": "gpt-4"}
        }
    )


class SettingsResponse(BaseSchema):
    """Settings response schema."""

    stash_url: str = Field(..., description="Stash server URL")
    stash_configured: bool = Field(..., description="Whether Stash is configured")
    openai_configured: bool = Field(..., description="Whether OpenAI is configured")
    openai_model: str = Field(..., description="OpenAI model")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment")


class ConnectionTestRequest(BaseSchema):
    """Request to test a connection."""

    service: str = Field(..., description="Service to test (stash or openai)")
    config: Optional[dict[str, str]] = Field(
        None, description="Optional config overrides"
    )


class ConnectionTestResponse(BaseSchema):
    """Connection test response."""

    service: str = Field(..., description="Service tested")
    success: bool = Field(..., description="Whether connection was successful")
    message: str = Field(..., description="Test result message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional details")


# Sync-related schemas
class SyncResultResponse(BaseSchema):
    """Sync result response."""

    job_id: Optional[str] = Field(None, description="Job ID")
    status: str = Field(..., description="Sync status")
    total_items: int = Field(..., description="Total items processed")
    processed_items: int = Field(..., description="Items processed")
    created_items: int = Field(..., description="Items created")
    updated_items: int = Field(..., description="Items updated")
    skipped_items: int = Field(0, description="Items skipped")
    failed_items: int = Field(..., description="Items failed")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Errors encountered"
    )


class SyncStatsResponse(BaseSchema):
    """Sync statistics response."""

    scene_count: int = Field(0, description="Total scenes in database")
    performer_count: int = Field(0, description="Total performers in database")
    tag_count: int = Field(0, description="Total tags in database")
    studio_count: int = Field(0, description="Total studios in database")
    last_scene_sync: Optional[str] = Field(
        None, description="Last scene sync timestamp"
    )
    last_performer_sync: Optional[str] = Field(
        None, description="Last performer sync timestamp"
    )
    last_tag_sync: Optional[str] = Field(None, description="Last tag sync timestamp")
    last_studio_sync: Optional[str] = Field(
        None, description="Last studio sync timestamp"
    )
    pending_scenes: int = Field(0, description="Scenes pending sync")
    pending_performers: int = Field(0, description="Performers pending sync")
    pending_tags: int = Field(0, description="Tags pending sync")
    pending_studios: int = Field(0, description="Studios pending sync")
    is_syncing: bool = Field(False, description="Whether a sync is currently running")


# Export all schemas
__all__ = [
    "BaseSchema",
    "PaginationParams",
    "HealthResponse",
    "VersionResponse",
    "ErrorResponse",
    "SuccessResponse",
    "PaginatedResponse",
    "PerformerResponse",
    "TagResponse",
    "StudioResponse",
    "JobStatus",
    "JobType",
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "JobDetailResponse",
    "JobsListResponse",
    "SceneBase",
    "SceneCreate",
    "SceneUpdate",
    "SceneResponse",
    "SceneFileResponse",
    "SceneFilter",
    "SceneSyncRequest",
    "AnalysisOptions",
    "AnalysisRequest",
    "ChangePreview",
    "SceneChanges",
    "AnalysisPlanCreate",
    "PlanResponse",
    "PlanDetailResponse",
    "AnalysisApplyRequest",
    "SettingsUpdate",
    "SettingsResponse",
    "ConnectionTestRequest",
    "ConnectionTestResponse",
    "SyncResultResponse",
    "SyncStatsResponse",
]
