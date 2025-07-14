"""Sync history tracking model."""
from sqlalchemy import Column, String, Integer, DateTime, JSON, func
from app.models.base import BaseModel


class SyncHistory(BaseModel):
    """
    Track sync operations history for auditing and incremental sync.
    """
    
    __tablename__ = "sync_history"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)  # 'scene', 'performer', 'tag', 'studio', 'all'
    job_id = Column(String, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String, nullable=False)  # 'in_progress', 'completed', 'failed', 'partial'
    items_synced = Column(Integer, default=0)
    items_created = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_details = Column(JSON)  # Store error information
    
    @property
    def duration_seconds(self):
        """Calculate sync duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self):
        """Calculate success rate."""
        if self.items_synced == 0:
            return 0.0
        return (self.items_synced - self.items_failed) / self.items_synced