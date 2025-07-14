"""Job model for tracking background tasks."""
import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class JobStatus(str, enum.Enum):
    """Status of a background job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    """Type of background job."""
    SYNC = "sync"
    ANALYSIS = "analysis"
    APPLY_PLAN = "apply_plan"
    EXPORT = "export"
    IMPORT = "import"
    CLEANUP = "cleanup"


class Job(BaseModel):
    """
    Model for tracking background jobs and their progress.
    
    Jobs are used to track long-running operations like syncing with Stash,
    running AI analysis, or applying analysis plans.
    """
    
    # UUID primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Job information
    type = Column(Enum(JobType), nullable=False, index=True)
    status = Column(
        Enum(JobStatus),
        nullable=False,
        default=JobStatus.PENDING,
        index=True
    )
    
    # Progress tracking
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    total_items = Column(Integer, nullable=True)
    processed_items = Column(Integer, default=0, nullable=False)
    
    # Results and errors
    result = Column(JSON, nullable=True)  # Job-specific results
    error = Column(Text, nullable=True)  # Error message if failed
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_job_type_status", "type", "status"),
        Index("idx_job_status_created", "status", "created_at"),
        Index("idx_job_completed", "completed_at"),
    )
    
    def update_progress(self, processed: Optional[int] = None, total: Optional[int] = None) -> None:
        """
        Update job progress.
        
        Args:
            processed: Number of items processed
            total: Total number of items
        """
        if processed is not None:
            self.processed_items = processed
        if total is not None:
            self.total_items = total
            
        # Calculate percentage
        if self.total_items and self.total_items > 0:
            self.progress = int((self.processed_items / self.total_items) * 100)
        else:
            self.progress = 0
    
    def mark_started(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.progress = 0
    
    def mark_completed(self, result: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark job as completed.
        
        Args:
            result: Optional result data
        """
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 100
        if result:
            self.result = result
    
    def mark_failed(self, error: str) -> None:
        """
        Mark job as failed.
        
        Args:
            error: Error message
        """
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
    
    def mark_cancelled(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if not self.started_at:
            return None
            
        end_time = self.completed_at or datetime.utcnow()
        duration = end_time - self.started_at
        return duration.total_seconds()
    
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == JobStatus.RUNNING
    
    def is_finished(self) -> bool:
        """Check if job has finished (success, failure, or cancelled)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    def can_be_cancelled(self) -> bool:
        """Check if job can be cancelled."""
        return self.status in [JobStatus.PENDING, JobStatus.RUNNING]
    
    def add_result_data(self, key: str, value: Any) -> None:
        """Add data to job result."""
        if self.result is None:
            self.result = {}
        self.result[key] = value
    
    def to_dict(self, exclude: set = None) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        data = super().to_dict(exclude)
        
        # Add computed fields
        data["duration_seconds"] = self.get_duration_seconds()
        data["is_running"] = self.is_running()
        data["is_finished"] = self.is_finished()
        data["can_cancel"] = self.can_be_cancelled()
        
        return data