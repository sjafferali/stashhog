"""Analysis plan model for managing batch metadata changes."""

import enum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Column, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.plan_change import PlanChange


class PlanStatus(str, enum.Enum):
    """Status of an analysis plan."""

    PENDING = "PENDING"  # Plan is being actively built during analysis
    DRAFT = "DRAFT"
    REVIEWING = "REVIEWING"
    APPLIED = "APPLIED"
    CANCELLED = "CANCELLED"


class AnalysisPlan(BaseModel):
    """
    Model for storing analysis plans that batch multiple metadata changes.

    Each plan contains multiple PlanChange entries that can be reviewed
    and applied as a batch.
    """

    # Auto-increment primary key
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Plan information
    name = Column(String(), nullable=False, index=True)
    description = Column(Text(), nullable=True)
    plan_metadata = Column(
        JSON, nullable=False, default=dict
    )  # Settings used, statistics, etc.
    status: Column = Column(
        Enum(PlanStatus), nullable=False, default=PlanStatus.DRAFT, index=True
    )

    # Link to the job that created this plan
    job_id = Column(String(), nullable=True, index=True)

    # Timestamps (created_at and updated_at from BaseModel)
    applied_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    changes = relationship(
        "PlanChange",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="PlanChange.id",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_plan_status_created", "status", "created_at"),
        Index("idx_plan_status_applied", "status", "applied_at"),
    )

    def get_change_count(self) -> int:
        """Get total number of changes in this plan."""
        return int(
            self.changes.count()
            if hasattr(self.changes, "count")
            else len(list(self.changes))
        )

    def get_applied_change_count(self) -> int:
        """Get number of applied changes."""
        from app.models.plan_change import ChangeStatus

        return int(self.changes.filter_by(status=ChangeStatus.APPLIED).count())

    def get_accepted_change_count(self) -> int:
        """Get number of accepted changes (approved but not yet applied)."""
        from app.models.plan_change import ChangeStatus

        return int(self.changes.filter_by(status=ChangeStatus.APPROVED).count())

    def get_pending_change_count(self) -> int:
        """Get number of pending changes (not yet reviewed)."""
        from app.models.plan_change import ChangeStatus

        return int(self.changes.filter_by(status=ChangeStatus.PENDING).count())

    def get_rejected_change_count(self) -> int:
        """Get number of rejected changes."""
        from app.models.plan_change import ChangeStatus

        return int(self.changes.filter_by(status=ChangeStatus.REJECTED).count())

    def get_changes_by_field(self, field: str) -> list["PlanChange"]:
        """Get all changes for a specific field."""
        return list(self.changes.filter_by(field=field).all())

    def get_changes_by_scene(self, scene_id: str) -> list["PlanChange"]:
        """Get all changes for a specific scene."""
        return list(self.changes.filter_by(scene_id=scene_id).all())

    def add_metadata(self, key: str, value: Any) -> None:
        """Add or update metadata entry."""
        if self.plan_metadata is None:
            self.plan_metadata = {}
        self.plan_metadata[key] = value

    def get_metadata(self, key: str, default: Optional[Any] = None) -> Any:
        """Get metadata entry."""
        if self.plan_metadata is None:
            return default
        return self.plan_metadata.get(key, default)

    def update_status_based_on_changes(self) -> None:
        """Update plan status based on change states."""
        total = self.get_change_count()
        if total == 0:
            return

        applied = self.get_applied_change_count()
        accepted = self.get_accepted_change_count()
        rejected = self.get_rejected_change_count()
        pending = self.get_pending_change_count()

        # If we're in DRAFT and some changes have been accepted/rejected, move to REVIEWING
        if self.status == PlanStatus.DRAFT and (accepted > 0 or rejected > 0):
            self.status = PlanStatus.REVIEWING  # type: ignore[assignment]

        # Only mark as APPLIED when:
        # 1. There are no pending changes (all changes have been reviewed)
        # 2. There are no approved changes left (all approved changes have been applied)
        # 3. There's at least one applied change
        if pending == 0 and accepted == 0 and applied > 0:
            self.status = PlanStatus.APPLIED  # type: ignore[assignment]
            if not self.applied_at:
                from datetime import datetime, timezone

                self.applied_at = datetime.now(timezone.utc)  # type: ignore[assignment]

    def can_be_applied(self) -> bool:
        """Check if plan can be applied."""
        return bool(self.status in [PlanStatus.DRAFT, PlanStatus.REVIEWING])

    def can_be_modified(self) -> bool:
        """Check if plan can be modified."""
        return bool(self.status == PlanStatus.DRAFT)

    def to_dict(
        self, exclude: Optional[set] = None, include_stats: bool = True
    ) -> dict[str, Any]:
        """Convert to dictionary with optional statistics."""
        data = super().to_dict(exclude)

        if include_stats:
            data["total_changes"] = self.get_change_count()
            data["applied_changes"] = self.get_applied_change_count()
            data["pending_changes"] = self.get_pending_change_count()

        return data
