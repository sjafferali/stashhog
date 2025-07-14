from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class SyncStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class SyncError:
    entity_type: str
    entity_id: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


@dataclass
class SyncStats:
    scenes_processed: int = 0
    scenes_created: int = 0
    scenes_updated: int = 0
    scenes_skipped: int = 0
    scenes_failed: int = 0
    
    performers_processed: int = 0
    performers_created: int = 0
    performers_updated: int = 0
    
    tags_processed: int = 0
    tags_created: int = 0
    tags_updated: int = 0
    
    studios_processed: int = 0
    studios_created: int = 0
    studios_updated: int = 0


@dataclass
class SyncResult:
    job_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: SyncStatus = SyncStatus.SUCCESS
    total_items: int = 0
    processed_items: int = 0
    created_items: int = 0
    updated_items: int = 0
    skipped_items: int = 0
    failed_items: int = 0
    errors: List[SyncError] = field(default_factory=list)
    stats: SyncStats = field(default_factory=SyncStats)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        if self.processed_items == 0:
            return 0.0
        return (self.processed_items - self.failed_items) / self.processed_items
    
    def add_error(self, entity_type: str, entity_id: str, error_message: str, details: Optional[Dict[str, Any]] = None):
        self.errors.append(SyncError(
            entity_type=entity_type,
            entity_id=entity_id,
            error_message=error_message,
            details=details
        ))
        self.failed_items += 1
        
        if entity_type == "scene":
            self.stats.scenes_failed += 1
    
    def complete(self, status: Optional[SyncStatus] = None):
        self.completed_at = datetime.utcnow()
        if status:
            self.status = status
        elif self.failed_items > 0:
            self.status = SyncStatus.PARTIAL if self.processed_items > self.failed_items else SyncStatus.FAILED
        else:
            self.status = SyncStatus.SUCCESS