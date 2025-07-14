from typing import Optional, List, Dict, Any, Callable
import logging

from app.models.job import JobType
from app.services.sync.sync_service import sync_service
from app.services.job_service import job_service


logger = logging.getLogger(__name__)


async def sync_all_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    force: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Execute full synchronization from Stash as a background job."""
    logger.info(f"Starting sync_all job {job_id} with force={force}")
    
    # Execute sync with progress callback
    result = await sync_service.sync_all(
        job_id=job_id,
        force=force,
        progress_callback=progress_callback
    )
    
    return result.dict()


async def sync_scenes_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    scene_ids: Optional[List[str]] = None,
    force: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Sync specific scenes as a background job."""
    logger.info(f"Starting sync_scenes job {job_id} for {len(scene_ids or [])} scenes")
    
    # Execute sync with progress callback
    result = await sync_service.sync_scenes(
        scene_ids=scene_ids,
        job_id=job_id,
        force=force,
        progress_callback=progress_callback
    )
    
    return result.dict()


async def sync_performers_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    force: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Sync performers as a background job."""
    logger.info(f"Starting sync_performers job {job_id}")
    
    # Execute sync with progress callback
    result = await sync_service.sync_performers(
        job_id=job_id,
        force=force,
        progress_callback=progress_callback
    )
    
    return result.dict()


async def sync_tags_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    force: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Sync tags as a background job."""
    logger.info(f"Starting sync_tags job {job_id}")
    
    # Execute sync with progress callback
    result = await sync_service.sync_tags(
        job_id=job_id,
        force=force,
        progress_callback=progress_callback
    )
    
    return result.dict()


async def sync_studios_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    force: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Sync studios as a background job."""
    logger.info(f"Starting sync_studios job {job_id}")
    
    # Execute sync with progress callback
    result = await sync_service.sync_studios(
        job_id=job_id,
        force=force,
        progress_callback=progress_callback
    )
    
    return result.dict()


def register_sync_jobs():
    """Register all sync job handlers with the job service."""
    job_service.register_handler(JobType.SYNC, sync_all_job)
    job_service.register_handler(JobType.SYNC_SCENES, sync_scenes_job)
    job_service.register_handler(JobType.SYNC_PERFORMERS, sync_performers_job)
    job_service.register_handler(JobType.SYNC_TAGS, sync_tags_job)
    job_service.register_handler(JobType.SYNC_STUDIOS, sync_studios_job)
    
    logger.info("Registered all sync job handlers")