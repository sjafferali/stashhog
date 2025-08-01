"""
Pydantic schemas for daemon API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DaemonResponse(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool
    auto_start: bool
    status: str
    configuration: Dict[str, Any]
    started_at: Optional[datetime]
    last_heartbeat: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DaemonUpdateRequest(BaseModel):
    configuration: Dict[str, Any] = Field(default_factory=dict)
    enabled: Optional[bool] = None
    auto_start: Optional[bool] = None


class DaemonLogResponse(BaseModel):
    id: str
    daemon_id: str
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class DaemonJobHistoryResponse(BaseModel):
    id: str
    daemon_id: str
    job_id: str
    action: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DaemonHealthItem(BaseModel):
    id: str
    name: str
    uptime: Optional[float] = None
    reason: Optional[str] = None
    last_heartbeat: Optional[str] = None


class DaemonHealthResponse(BaseModel):
    healthy: List[DaemonHealthItem]
    unhealthy: List[DaemonHealthItem]
    stopped: List[DaemonHealthItem]
