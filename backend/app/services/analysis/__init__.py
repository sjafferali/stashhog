"""Analysis service package for scene metadata detection and AI analysis."""

from .models import (
    AnalysisOptions,
    ProposedChange,
    SceneChanges,
    DetectionResult,
    ApplyResult
)
from .analysis_service import AnalysisService
from .plan_manager import PlanManager
from .ai_client import AIClient
from .batch_processor import BatchProcessor
from .studio_detector import StudioDetector
from .performer_detector import PerformerDetector
from .tag_detector import TagDetector
from .details_generator import DetailsGenerator

__all__ = [
    "AnalysisOptions",
    "ProposedChange", 
    "SceneChanges",
    "DetectionResult",
    "ApplyResult",
    "AnalysisService",
    "PlanManager",
    "AIClient",
    "BatchProcessor",
    "StudioDetector",
    "PerformerDetector",
    "TagDetector",
    "DetailsGenerator"
]