"""Sync history tracking model."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.models.base import BaseModel


class SyncHistory(BaseModel):
    """
    Track sync operations history for auditing and incremental sync.
    """

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(
        String, nullable=False, index=True
    )  # 'scene', 'performer', 'tag', 'studio', 'all'
    job_id = Column(String, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    status = Column(
        String, nullable=False
    )  # 'in_progress', 'completed', 'failed', 'partial'
    items_synced = Column(Integer, default=0)
    items_created = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_details = Column(JSON)  # Store error information

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate sync duration in seconds."""
        if self.completed_at:
            return float((self.completed_at - self.started_at).total_seconds())
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.items_synced == 0:
            return 0.0
        return float((self.items_synced - self.items_failed) / self.items_synced)

    def get_details(self) -> Optional[Dict[str, Any]]:
        """Get error details."""
        return self.error_details  # type: ignore[return-value]

    def is_recent(self, hours: int = 24) -> bool:
        """Check if sync was recent."""
        if not self.started_at:
            return False
        now = datetime.utcnow()
        return bool((now - self.started_at).total_seconds() < hours * 3600)
