"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

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
    features: Optional[Dict[str, bool]] = Field(None, description="Enabled features")


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
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(
        cls, items: List[T], total: int, page: int, per_page: int
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


class JobType(str, Enum):
    """Job type enumeration."""

    SCENE_SYNC = "scene_sync"
    SCENE_ANALYSIS = "scene_analysis"
    BATCH_ANALYSIS = "batch_analysis"
    SETTINGS_TEST = "settings_test"
    SYNC_ALL = "sync_all"
    SYNC = "sync"  # Legacy, mapped to SYNC_ALL
    SYNC_SCENES = "sync_scenes"
    SYNC_PERFORMERS = "sync_performers"
    SYNC_TAGS = "sync_tags"
    SYNC_STUDIOS = "sync_studios"
    ANALYSIS = "analysis"
    APPLY_PLAN = "apply_plan"


class JobCreate(BaseSchema):
    """Schema for creating a job."""

    type: JobType = Field(..., description="Job type")
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {}, description="Job parameters"
    )


class JobUpdate(BaseSchema):
    """Schema for updating a job."""

    status: Optional[JobStatus] = Field(None, description="Job status")
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message")


class JobResponse(BaseSchema):
    """Job response schema."""

    id: str = Field(..., description="Job ID")
    type: JobType = Field(..., description="Job type")
    status: JobStatus = Field(..., description="Job status")
    progress: float = Field(0, description="Progress percentage")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Job parameters"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class JobDetailResponse(JobResponse):
    """Detailed job response with additional information."""

    logs: Optional[List[str]] = Field(None, description="Job logs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Job metadata")


# Entity schemas
class PerformerResponse(BaseSchema):
    """Performer response schema."""

    id: str = Field(..., description="Performer ID")
    name: str = Field(..., description="Performer name")
    scene_count: Optional[int] = Field(None, description="Number of scenes")


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
class SceneBase(BaseSchema):
    """Base scene schema."""

    id: str = Field(..., description="Scene ID")
    title: str = Field(..., description="Scene title")
    paths: List[str] = Field(..., description="File paths")
    organized: bool = Field(..., description="Is scene organized")
    details: Optional[str] = Field(None, description="Scene details/description")
    created_date: datetime = Field(..., description="Creation date in Stash")
    scene_date: Optional[datetime] = Field(None, description="Scene date")


class SceneCreate(SceneBase):
    """Schema for creating a scene."""

    pass


class SceneUpdate(SceneBase):
    """Schema for updating a scene."""

    tags: Optional[List[str]] = Field(None, description="Scene tags")
    performers: Optional[List[str]] = Field(None, description="Scene performers")
    studio: Optional[str] = Field(None, description="Studio name")


class SceneResponse(SceneBase):
    """Scene response schema."""

    studio: Optional[StudioResponse] = Field(None, description="Studio")
    performers: List[PerformerResponse] = Field(
        default_factory=list, description="Scene performers"
    )
    tags: List[TagResponse] = Field(default_factory=list, description="Scene tags")
    last_synced: datetime = Field(..., description="Last sync timestamp")

    # Metadata fields
    date: Optional[datetime] = Field(None, description="Scene date")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    size: Optional[int] = Field(None, description="File size in bytes")
    width: Optional[int] = Field(None, description="Video width")
    height: Optional[int] = Field(None, description="Video height")
    framerate: Optional[float] = Field(None, description="Frame rate")
    bitrate: Optional[int] = Field(None, description="Bitrate in kbps")
    video_codec: Optional[str] = Field(None, description="Video codec")


class SceneFilter(BaseSchema):
    """Scene filter parameters."""

    search: Optional[str] = Field(None, description="Search text")
    studio_id: Optional[str] = Field(None, description="Filter by studio ID")
    performer_ids: Optional[List[str]] = Field(
        None, description="Filter by performer IDs"
    )
    tag_ids: Optional[List[str]] = Field(None, description="Filter by tag IDs")
    organized: Optional[bool] = Field(None, description="Filter by organized status")
    date_from: Optional[datetime] = Field(None, description="Filter by date from")
    date_to: Optional[datetime] = Field(None, description="Filter by date to")


class SceneSyncRequest(BaseSchema):
    """Request to sync scenes from Stash."""

    filter: Optional[Dict[str, Any]] = Field(None, description="Stash filter criteria")
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
    use_ai: bool = Field(True, description="Use AI for detection")
    confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class AnalysisRequest(BaseSchema):
    """Analysis request schema."""

    scene_ids: Optional[List[str]] = Field(
        None, description="Specific scene IDs to analyze"
    )
    filters: Optional[SceneFilter] = Field(None, description="Scene filters")
    options: AnalysisOptions = Field(
        default_factory=lambda: AnalysisOptions(
            detect_performers=True,
            detect_studios=True,
            detect_tags=True,
            detect_details=True,
            use_ai=True,
            confidence_threshold=0.7,
        ),
        description="Analysis options",
    )
    plan_name: str = Field(..., description="Name for the analysis plan")


class ChangePreview(BaseSchema):
    """Preview of a single change."""

    field: str = Field(..., description="Field to change")
    action: str = Field(..., description="Action type (add, update, remove)")
    current_value: Any = Field(..., description="Current value")
    proposed_value: Any = Field(..., description="Proposed value")
    confidence: float = Field(..., description="Confidence score")


class SceneChanges(BaseSchema):
    """Changes for a single scene."""

    scene_id: str = Field(..., description="Scene ID")
    scene_title: str = Field(..., description="Scene title")
    changes: List[ChangePreview] = Field(..., description="List of changes")


class AnalysisPlanCreate(BaseSchema):
    """Schema for creating an analysis plan."""

    scene_ids: Optional[List[str]] = Field(
        None, description="Specific scene IDs to analyze"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Filters for scene selection"
    )
    detect_performers: bool = Field(True, description="Detect performers")
    detect_studios: bool = Field(True, description="Detect studios")
    detect_tags: bool = Field(True, description="Detect tags")
    detect_details: bool = Field(True, description="Generate/enhance details")
    use_ai: bool = Field(True, description="Use AI for detection")
    confidence_threshold: float = Field(0.7, description="Minimum confidence threshold")


class PlanResponse(BaseSchema):
    """Analysis plan response schema."""

    id: int = Field(..., description="Plan ID")
    name: str = Field(..., description="Plan name")
    status: str = Field(..., description="Plan status")
    created_at: datetime = Field(..., description="Creation timestamp")
    total_scenes: int = Field(..., description="Total scenes analyzed")
    total_changes: int = Field(..., description="Total proposed changes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Plan metadata")


class PlanDetailResponse(PlanResponse):
    """Detailed analysis plan response with changes."""

    scenes: List[SceneChanges] = Field(..., description="Changes grouped by scene")


class AnalysisApplyRequest(BaseSchema):
    """Request to apply an analysis plan."""

    apply_tags: bool = Field(True, description="Apply suggested tags")
    apply_performers: bool = Field(True, description="Apply suggested performers")
    apply_details: bool = Field(True, description="Apply suggested details")
    custom_modifications: Optional[Dict[str, Any]] = Field(
        None, description="Custom modifications"
    )


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
    config: Optional[Dict[str, str]] = Field(
        None, description="Optional config overrides"
    )


class ConnectionTestResponse(BaseSchema):
    """Connection test response."""

    service: str = Field(..., description="Service tested")
    success: bool = Field(..., description="Whether connection was successful")
    message: str = Field(..., description="Test result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


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
    errors: List[Dict[str, Any]] = Field(
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
    "SceneBase",
    "SceneCreate",
    "SceneUpdate",
    "SceneResponse",
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
