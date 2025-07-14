from typing import Optional, List, Dict, Any, Callable
import logging

from app.models.job import JobType
from app.models.analysis import AnalysisOptions
from app.services.analysis.analysis_service import analysis_service
from app.services.job_service import job_service


logger = logging.getLogger(__name__)


async def analyze_scenes_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    scene_ids: Optional[List[str]] = None,
    options: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Execute scene analysis as a background job."""
    logger.info(f"Starting analyze_scenes job {job_id} for {len(scene_ids or [])} scenes")
    
    # Convert options dict to AnalysisOptions
    analysis_options = AnalysisOptions(**options) if options else AnalysisOptions()
    
    # Execute analysis with progress callback
    plan = await analysis_service.analyze_scenes(
        scene_ids=scene_ids,
        options=analysis_options,
        job_id=job_id,
        progress_callback=progress_callback
    )
    
    return {
        "plan_id": plan.id,
        "total_changes": len(plan.changes),
        "scenes_analyzed": len(plan.scenes_analyzed),
        "summary": {
            "performers_to_add": len([c for c in plan.changes if c.field == "performers" and c.action == "add"]),
            "tags_to_add": len([c for c in plan.changes if c.field == "tags" and c.action == "add"]),
            "studios_to_set": len([c for c in plan.changes if c.field == "studio" and c.action == "set"]),
            "titles_to_update": len([c for c in plan.changes if c.field == "title" and c.action == "set"])
        }
    }


async def apply_analysis_plan_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    plan_id: str,
    auto_approve: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Apply an analysis plan as a background job."""
    logger.info(f"Starting apply_analysis_plan job {job_id} for plan {plan_id}")
    
    # Execute plan application with progress callback
    result = await analysis_service.apply_plan(
        plan_id=plan_id,
        auto_approve=auto_approve,
        job_id=job_id,
        progress_callback=progress_callback
    )
    
    return {
        "plan_id": plan_id,
        "applied_changes": result.applied_changes,
        "failed_changes": result.failed_changes,
        "skipped_changes": result.skipped_changes,
        "total_changes": result.total_changes,
        "success_rate": (result.applied_changes / result.total_changes * 100) if result.total_changes > 0 else 0
    }


async def analyze_all_unanalyzed_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    options: Optional[Dict[str, Any]] = None,
    batch_size: int = 100,
    **kwargs
) -> Dict[str, Any]:
    """Analyze all unanalyzed scenes as a background job."""
    logger.info(f"Starting analyze_all_unanalyzed job {job_id}")
    
    # Convert options dict to AnalysisOptions
    analysis_options = AnalysisOptions(**options) if options else AnalysisOptions()
    
    # Get unanalyzed scenes
    from app.repositories.scene_repository import scene_repository
    from app.core.database import get_db
    
    db = next(get_db())
    try:
        unanalyzed_scenes = await scene_repository.get_unanalyzed_scenes(db)
        scene_ids = [scene.id for scene in unanalyzed_scenes]
        
        logger.info(f"Found {len(scene_ids)} unanalyzed scenes")
        
        # Execute analysis in batches
        total_scenes = len(scene_ids)
        analyzed_count = 0
        all_plans = []
        
        for i in range(0, total_scenes, batch_size):
            batch = scene_ids[i:i + batch_size]
            batch_progress = int((i / total_scenes) * 100)
            
            await progress_callback(
                batch_progress,
                f"Analyzing batch {i // batch_size + 1} of {(total_scenes + batch_size - 1) // batch_size}"
            )
            
            # Analyze batch
            plan = await analysis_service.analyze_scenes(
                scene_ids=batch,
                options=analysis_options,
                job_id=f"{job_id}_batch_{i // batch_size}",
                progress_callback=lambda p, m: None  # Don't report individual progress
            )
            
            all_plans.append(plan)
            analyzed_count += len(batch)
        
        # Summary
        total_changes = sum(len(plan.changes) for plan in all_plans)
        
        return {
            "scenes_analyzed": analyzed_count,
            "total_changes": total_changes,
            "plans_created": len(all_plans),
            "plan_ids": [plan.id for plan in all_plans]
        }
    finally:
        db.close()


def register_analysis_jobs():
    """Register all analysis job handlers with the job service."""
    job_service.register_handler(JobType.ANALYSIS, analyze_scenes_job)
    job_service.register_handler(JobType.APPLY_PLAN, apply_analysis_plan_job)
    
    logger.info("Registered all analysis job handlers")