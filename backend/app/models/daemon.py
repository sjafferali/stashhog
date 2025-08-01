import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Set

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
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
    METADATA_GENERATE_WATCHER = "metadata_generate_watcher"


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
    MONITORED = "MONITORED"


class Daemon(BaseModel):
    __tablename__: str = "daemons"  # type: ignore[assignment]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    auto_start = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default=DaemonStatus.STOPPED.value)
    configuration = Column(JSONBType, nullable=True, default=dict)
    started_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

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
    action = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    daemon = relationship("Daemon", back_populates="job_history")
    job = relationship("Job")

    def to_dict(self, exclude: Optional[Set[Any]] = None) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "daemon_id": str(self.daemon_id),
            "job_id": str(self.job_id),
            "action": self.action,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }
