import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes

from app.core.database import Base
from app.models.base import BaseModel


# Custom type that uses JSONB for PostgreSQL and JSON for other databases
class JSONBType(sqltypes.TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


class DaemonType(str, enum.Enum):
    TEST_DAEMON = "test_daemon"
    AUTO_VIDEO_ANALYSIS_DAEMON = "auto_video_analysis_daemon"
    AUTO_PLAN_APPLIER_DAEMON = "auto_plan_applier_daemon"
    AUTO_STASH_SYNC_DAEMON = "auto_stash_sync_daemon"
    DOWNLOAD_PROCESSOR_DAEMON = "download_processor_daemon"
    AUTO_STASH_GENERATION_DAEMON = "auto_stash_generation_daemon"


class DaemonStatus(str, enum.Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class LogLevel(str, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DaemonJobAction(str, enum.Enum):
    LAUNCHED = "LAUNCHED"
    CANCELLED = "CANCELLED"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class Daemon(BaseModel):
    __tablename__: str = "daemons"  # type: ignore[assignment]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    auto_start = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default=DaemonStatus.STOPPED.value)
    configuration = Column(JSONBType, nullable=True, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
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
    logs = relationship(
        "DaemonLog", back_populates="daemon", cascade="all, delete-orphan"
    )
    job_history = relationship(
        "DaemonJobHistory", back_populates="daemon", cascade="all, delete-orphan"
    )

    def to_dict(self, exclude: Optional[Set[Any]] = None) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "status": self.status,
            "configuration": self.configuration or {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DaemonLog(Base):
    __tablename__: str = "daemon_logs"  # type: ignore[assignment]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    daemon = relationship("Daemon", back_populates="logs")

    def to_dict(self, exclude: Optional[Set[Any]] = None) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "level": self.level,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


class DaemonJobHistory(Base):
    __tablename__: str = "daemon_job_history"  # type: ignore[assignment]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daemon_id = Column(
        UUID(as_uuid=True), ForeignKey("daemons.id", ondelete="CASCADE"), nullable=False
    )
    job_id = Column(String, ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    action: Column = Column(Enum(DaemonJobAction), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    daemon = relationship("Daemon", back_populates="job_history")
    job = relationship("Job")

    def to_dict(self, exclude: Optional[Set[Any]] = None) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "job_id": str(self.job_id),
            "action": (
                self.action.value
                if isinstance(self.action, DaemonJobAction)
                else self.action
            ),
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }
