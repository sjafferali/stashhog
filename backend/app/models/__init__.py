"""
Database models package.

This module imports and exports all database models to ensure they are
registered with SQLAlchemy when the application starts.
"""

# Import base model and database
from app.models.base import BaseModel

# Import association tables (must be imported before models that use them)
from app.models.associations import scene_performer, scene_tag

# Import all models
from app.models.scene import Scene
from app.models.performer import Performer
from app.models.tag import Tag
from app.models.studio import Studio
from app.models.analysis_plan import AnalysisPlan, PlanStatus
from app.models.plan_change import PlanChange, ChangeAction
from app.models.job import Job, JobStatus, JobType
from app.models.setting import Setting
from app.models.scheduled_task import ScheduledTask
from app.models.sync_history import SyncHistory

# Export all models and enums
__all__ = [
    # Base
    "BaseModel",
    
    # Association tables
    "scene_performer",
    "scene_tag",
    
    # Models
    "Scene",
    "Performer", 
    "Tag",
    "Studio",
    "AnalysisPlan",
    "PlanChange",
    "Job",
    "Setting",
    "ScheduledTask",
    "SyncHistory",
    
    # Enums
    "PlanStatus",
    "ChangeAction",
    "JobStatus",
    "JobType",
]