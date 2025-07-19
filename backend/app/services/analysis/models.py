"""Data models for the analysis service."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


@dataclass
class AnalysisOptions:
    """Options for controlling scene analysis behavior."""

    detect_performers: bool = False
    detect_studios: bool = False
    detect_tags: bool = False
    detect_details: bool = False
    detect_video_tags: bool = False
    confidence_threshold: float = 0.7
    batch_size: int = 15


@dataclass
class ProposedChange:
    """Represents a single proposed change to a scene."""

    field: str  # "performers", "studio", "tags", "details"
    action: str  # "add", "remove", "update", "set"
    current_value: Any
    proposed_value: Any
    confidence: float
    reason: Optional[str] = None

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this change meets the confidence threshold."""
        return self.confidence >= threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "field": self.field,
            "action": self.action,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class SceneChanges:
    """Collection of proposed changes for a single scene."""

    scene_id: str
    scene_title: str
    scene_path: str
    changes: List[ProposedChange] = field(default_factory=list)
    error: Optional[str] = None

    def has_changes(self) -> bool:
        """Check if there are any proposed changes."""
        return len(self.changes) > 0

    def get_changes_by_field(self, field: str) -> List[ProposedChange]:
        """Get all changes for a specific field."""
        return [c for c in self.changes if c.field == field]

    def get_high_confidence_changes(
        self, threshold: float = 0.8
    ) -> List[ProposedChange]:
        """Get only high confidence changes."""
        return [c for c in self.changes if c.is_high_confidence(threshold)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scene_id": self.scene_id,
            "scene_title": self.scene_title,
            "scene_path": self.scene_path,
            "changes": [c.to_dict() for c in self.changes],
            "error": self.error,
        }


@dataclass
class DetectionResult:
    """Result from a detection operation."""

    value: Any  # The detected value(s)
    confidence: float
    source: str = "ai"  # "ai", "path", "pattern", "manual"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self, threshold: float = 0.7) -> bool:
        """Check if detection meets confidence threshold."""
        return self.confidence >= threshold


@dataclass
class ApplyResult:
    """Result of applying changes to Stash."""

    plan_id: int
    total_changes: int
    applied_changes: int
    failed_changes: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    applied_at: datetime = field(default_factory=datetime.utcnow)
    scenes_analyzed: int = 0
    skipped_changes: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of applied changes."""
        if self.total_changes == 0:
            return 1.0
        return self.applied_changes / self.total_changes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "plan_id": self.plan_id,
            "total_changes": self.total_changes,
            "applied_changes": self.applied_changes,
            "failed_changes": self.failed_changes,
            "success_rate": self.success_rate,
            "errors": self.errors,
            "applied_at": self.applied_at.isoformat(),
        }


# Pydantic models for AI responses
class TagSuggestion(BaseModel):
    """Single tag suggestion from AI."""

    name: str = Field(description="The tag name")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence score"
    )


class TagSuggestionsResponse(BaseModel):
    """Response format for tag suggestions."""

    tags: List[TagSuggestion] = Field(
        default_factory=list, description="List of suggested tags"
    )


class DetailsResponse(BaseModel):
    """Response format for scene details generation."""

    description: str = Field(description="Generated scene description")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence score"
    )
