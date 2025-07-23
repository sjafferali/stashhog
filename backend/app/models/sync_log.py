from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base_log import BaseLogModel


class SyncLog(BaseLogModel):
    __tablename__ = "sync_log"  # type: ignore[assignment]

    id = Column(Integer, primary_key=True, index=True)
    sync_history_id = Column(Integer, ForeignKey("sync_history.id"), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, index=True)
    sync_type = Column(String, nullable=False)  # 'full', 'incremental', 'specific'
    had_changes = Column(Boolean, default=False)
    change_type = Column(String)  # 'created', 'updated', 'skipped', 'failed'
    error_message = Column(Text)

    # Relationship
    sync_history = relationship("SyncHistory", backref="sync_logs")
