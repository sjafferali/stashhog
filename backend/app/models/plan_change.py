"""Plan change model for individual metadata modifications."""

import enum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.analysis_plan import AnalysisPlan  # noqa: F401
    from app.models.scene import Scene  # noqa: F401


class ChangeAction(str, enum.Enum):
    """Type of change action."""

    ADD = "add"  # Add item to list (performer, tag)
    REMOVE = "remove"  # Remove item from list
    UPDATE = "update"  # Update field value
    SET = "set"  # Set field value (for single values)


class ChangeStatus(str, enum.Enum):
    """Status of an individual change."""

    PENDING = "pending"  # Not yet reviewed
    APPROVED = "approved"  # Approved but not applied
    REJECTED = "rejected"  # Rejected, won't be applied
    APPLIED = "applied"  # Applied to Stash


class PlanChange(BaseModel):
    """
    Individual change within an analysis plan.

    Represents a single modification to a scene's metadata.
    """

    # Auto-increment primary key
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign keys
    plan_id = Column(
        Integer,
        ForeignKey("analysis_plan.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(
        String, ForeignKey("scene.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Change details
    field = Column(
        String(), nullable=False, index=True
    )  # performer, tag, studio, details, etc.
    action: Column = Column(Enum(ChangeAction), nullable=False, index=True)
    current_value = Column(JSON, nullable=True)  # Current value (for reference)
    proposed_value = Column(JSON, nullable=False)  # Proposed new value
    confidence = Column(Float(), nullable=True)  # AI confidence score (0-1)

    # Application tracking
    status: Column = Column(
        Enum(
            ChangeStatus,
            name="changestatus",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ChangeStatus.PENDING,
        index=True,
    )
    # Tracking fields
    applied: Column = Column(Boolean(), default=False, nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    plan = relationship("AnalysisPlan", back_populates="changes")
    scene = relationship("Scene", back_populates="plan_changes")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_change_plan_field", "plan_id", "field"),
        Index("idx_change_scene_field", "scene_id", "field"),
        Index("idx_change_applied_plan", "applied", "plan_id"),
        Index("idx_change_status_plan", "status", "plan_id"),
        Index("idx_change_confidence", "confidence"),
    )

    def get_display_value(self, value: Any) -> str:
        """Convert a value to display string."""
        if value is None:
            return "None"
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        if isinstance(value, dict):
            if "name" in value:
                return str(value["name"])
            if "id" in value and "name" in value:
                return f"{value['name']} ({value['id']})"
        return str(value)

    def get_change_description(self) -> str:
        """Get human-readable description of the change."""
        current = self.get_display_value(self.current_value)
        proposed = self.get_display_value(self.proposed_value)

        if self.action == ChangeAction.ADD:
            return f"Add {proposed} to {self.field}"
        elif self.action == ChangeAction.REMOVE:
            return f"Remove {proposed} from {self.field}"
        elif self.action == ChangeAction.UPDATE:
            return f"Update {self.field} from '{current}' to '{proposed}'"
        elif self.action == ChangeAction.SET:
            return f"Set {self.field} to '{proposed}'"
        else:
            return f"{self.action.value} {self.field}: {proposed}"

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this is a high-confidence change."""
        return bool(self.confidence is not None and self.confidence >= threshold)

    def can_be_applied(self) -> bool:
        """Check if this change can be applied."""
        return bool(
            not self.applied
            and self.status != ChangeStatus.REJECTED
            and self.plan.can_be_applied()
        )

    def to_dict(self, exclude: Optional[set] = None) -> dict[str, Any]:
        """Convert to dictionary with additional fields."""
        data = super().to_dict(exclude)

        # Add computed fields
        data["change_description"] = self.get_change_description()
        data["can_apply"] = self.can_be_applied()

        # Add scene title if loaded
        if hasattr(self, "scene") and self.scene:
            data["scene_title"] = self.scene.title

        return data
