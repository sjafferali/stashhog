"""Enhanced daemon observability models for tracking errors, metrics, and activities."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.daemon import JSONBType


class ErrorType(str, enum.Enum):
    CONNECTION = "CONNECTION"
    PROCESSING = "PROCESSING"
    CONFIGURATION = "CONFIGURATION"
    PERMISSION = "PERMISSION"
    RESOURCE = "RESOURCE"
    UNKNOWN = "UNKNOWN"


class ActivityType(str, enum.Enum):
    JOB_LAUNCHED = "JOB_LAUNCHED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    WARNING_OCCURRED = "WARNING_OCCURRED"
    STATUS_CHANGED = "STATUS_CHANGED"
    CONFIGURATION_CHANGED = "CONFIGURATION_CHANGED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
    QUEUE_PROCESSED = "QUEUE_PROCESSED"


class AlertType(str, enum.Enum):
    ERROR_THRESHOLD = "ERROR_THRESHOLD"
    STUCK_DAEMON = "STUCK_DAEMON"
    CRASH_DETECTED = "CRASH_DETECTED"
    HIGH_FAILURE_RATE = "HIGH_FAILURE_RATE"
    LONG_RUNNING_JOB = "LONG_RUNNING_JOB"
    HEARTBEAT_MISSED = "HEARTBEAT_MISSED"


class NotificationMethod(str, enum.Enum):
    UI = "UI"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"


class DaemonError(Base):
    """Track daemon errors with context and occurrence patterns."""

    __tablename__ = "daemon_errors"
    __table_args__ = (
        Index("idx_daemon_errors_daemon_id_last_seen", "daemon_id", "last_seen"),
        Index("idx_daemon_errors_error_type", "error_type"),
        Index("idx_daemon_errors_resolved", "resolved"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    error_type = Column(String(50), nullable=False, default=ErrorType.UNKNOWN.value)
    error_message = Column(Text, nullable=False)
    error_details = Column(Text, nullable=True)  # Stack trace or detailed error info
    context = Column(
        JSONBType, nullable=True
    )  # What was being processed when error occurred
    occurrence_count = Column(Integer, nullable=False, default=1)
    first_seen = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    daemon = relationship("Daemon", backref="errors")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "context": self.context,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class DaemonActivity(Base):
    """Track daemon activities for real-time monitoring."""

    __tablename__ = "daemon_activities"
    __table_args__ = (
        Index("idx_daemon_activities_daemon_id_created_at", "daemon_id", "created_at"),
        Index("idx_daemon_activities_activity_type", "activity_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    activity_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSONBType, nullable=True)  # Additional activity details
    severity = Column(
        String(20), nullable=False, default="info"
    )  # info, warning, error
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    daemon = relationship("Daemon", backref="activities")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "activity_type": self.activity_type,
            "message": self.message,
            "details": self.details,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DaemonMetric(Base):
    """Track daemon performance metrics over time."""

    __tablename__ = "daemon_metrics"
    __table_args__ = (
        UniqueConstraint(
            "daemon_id", "metric_name", "timestamp", name="uq_daemon_metric"
        ),
        Index("idx_daemon_metrics_daemon_id_timestamp", "daemon_id", "timestamp"),
        Index("idx_daemon_metrics_metric_name", "metric_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    metric_name = Column(
        String(100), nullable=False
    )  # e.g., "jobs_per_minute", "error_rate"
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(
        String(50), nullable=True
    )  # e.g., "count", "percentage", "seconds"
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    daemon = relationship("Daemon", backref="metrics")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class DaemonAlert(Base):
    """Configure and track alerts for daemon monitoring."""

    __tablename__ = "daemon_alerts"
    __table_args__ = (
        UniqueConstraint("daemon_id", "alert_type", name="uq_daemon_alert"),
        Index("idx_daemon_alerts_enabled", "enabled"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    alert_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=True)  # e.g., 5 errors in 10 minutes
    threshold_unit = Column(String(50), nullable=True)  # e.g., "errors_per_minute"
    notification_method = Column(
        String(50), nullable=False, default=NotificationMethod.UI.value
    )
    notification_config = Column(
        JSONBType, nullable=True
    )  # Email addresses, webhook URLs, etc.
    enabled = Column(Boolean, nullable=False, default=True)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    daemon = relationship("Daemon", backref="alerts")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "alert_type": self.alert_type,
            "threshold_value": self.threshold_value,
            "threshold_unit": self.threshold_unit,
            "notification_method": self.notification_method,
            "notification_config": self.notification_config,
            "enabled": self.enabled,
            "last_triggered": (
                self.last_triggered.isoformat() if self.last_triggered else None
            ),
            "trigger_count": self.trigger_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DaemonStatus(Base):
    """Track current daemon status and activity details."""

    __tablename__ = "daemon_status"
    __table_args__ = (UniqueConstraint("daemon_id", name="uq_daemon_status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    current_activity = Column(
        String(255), nullable=True
    )  # What the daemon is currently doing
    current_progress = Column(Float, nullable=True)  # Progress percentage (0-100)
    items_processed = Column(Integer, nullable=False, default=0)
    items_pending = Column(Integer, nullable=False, default=0)
    last_error_message = Column(Text, nullable=True)
    last_error_time = Column(DateTime(timezone=True), nullable=True)
    error_count_24h = Column(Integer, nullable=False, default=0)
    warning_count_24h = Column(Integer, nullable=False, default=0)
    jobs_launched_24h = Column(Integer, nullable=False, default=0)
    jobs_completed_24h = Column(Integer, nullable=False, default=0)
    jobs_failed_24h = Column(Integer, nullable=False, default=0)
    health_score = Column(Float, nullable=False, default=100.0)  # 0-100
    avg_job_duration_seconds = Column(Float, nullable=True)
    uptime_percentage = Column(Float, nullable=False, default=100.0)
    last_successful_run = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    daemon = relationship("Daemon", backref="status_info", uselist=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "current_activity": self.current_activity,
            "current_progress": self.current_progress,
            "items_processed": self.items_processed,
            "items_pending": self.items_pending,
            "last_error_message": self.last_error_message,
            "last_error_time": (
                self.last_error_time.isoformat() if self.last_error_time else None
            ),
            "error_count_24h": self.error_count_24h,
            "warning_count_24h": self.warning_count_24h,
            "jobs_launched_24h": self.jobs_launched_24h,
            "jobs_completed_24h": self.jobs_completed_24h,
            "jobs_failed_24h": self.jobs_failed_24h,
            "health_score": self.health_score,
            "avg_job_duration_seconds": self.avg_job_duration_seconds,
            "uptime_percentage": self.uptime_percentage,
            "last_successful_run": (
                self.last_successful_run.isoformat()
                if self.last_successful_run
                else None
            ),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
