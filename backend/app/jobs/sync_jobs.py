import logging
from typing import Any, Callable, Dict, List, Optional

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService
from app.services.sync.models import SyncStatus
from app.services.sync.sync_service import SyncService

logger = logging.getLogger(__name__)


async def sync_all_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    full_resync: bool = False,
    include_scenes: bool = True,
    include_performers: bool = True,
    include_tags: bool = True,
    include_studios: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute synchronization from Stash as a background job."""
    logger.info(f"Starting sync job {job_id} with full_resync={full_resync}")
    logger.info(
        f"Entity selection: scenes={include_scenes}, performers={include_performers}, tags={include_tags}, studios={include_studios}"
    )
    logger.debug(f"sync_all_job called with kwargs: {kwargs}")

    try:
        # Create services for this job
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise  # Re-raise for complete initialization failure

    async with AsyncSessionLocal() as db:
        logger.debug(f"Created database session: {type(db)}")
        sync_service = SyncService(stash_service, db)
        logger.debug("Created sync service instance")

        # Execute sync with progress callback
        logger.debug("About to call sync_service.sync_all")
        result = await sync_service.sync_all(
            job_id=job_id,
            force=full_resync,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
            include_scenes=include_scenes,
            include_performers=include_performers,
            include_tags=include_tags,
            include_studios=include_studios,
        )
        logger.debug(f"sync_all completed with status: {result.status}")

    # Convert SyncResult dataclass to dict manually
    job_result = {
        "job_id": result.job_id,
        "status": (
            result.status.value if hasattr(result.status, "value") else result.status
        ),
        "total_items": result.total_items,
        "processed_items": result.processed_items,
        "created_items": result.created_items,
        "updated_items": result.updated_items,
        "failed_items": result.failed_items,
        "duration_seconds": result.duration_seconds,
        "success_rate": result.success_rate,
        "errors": [error.to_dict() for error in result.errors] if result.errors else [],
    }

    # Map sync status to job status hint for the job service
    if result.status == SyncStatus.FAILED:
        job_result["status"] = "failed"
    elif result.status == SyncStatus.PARTIAL and result.errors:
        job_result["status"] = "completed_with_errors"

    return job_result


async def sync_scenes_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    scene_ids: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Sync specific scenes as a background job. Always performs full sync of specified scenes."""
    logger.info(f"Starting sync_scenes job {job_id} for {len(scene_ids or [])} scenes")

    try:
        # Create services for this job
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise  # Re-raise for complete initialization failure

    async with AsyncSessionLocal() as db:
        sync_service = SyncService(stash_service, db)

        # Execute sync with progress callback
        # Always use force=True for specific scene syncs
        result = await sync_service.sync_scenes(
            scene_ids=scene_ids,
            job_id=job_id,
            force=True,  # Always force sync for specific scenes
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    # Convert SyncResult dataclass to dict manually
    job_result = {
        "job_id": result.job_id,
        "status": (
            result.status.value if hasattr(result.status, "value") else result.status
        ),
        "total_items": result.total_items,
        "processed_items": result.processed_items,
        "created_items": result.created_items,
        "updated_items": result.updated_items,
        "failed_items": result.failed_items,
        "duration_seconds": result.duration_seconds,
        "success_rate": result.success_rate,
        "errors": [error.to_dict() for error in result.errors] if result.errors else [],
    }

    # Map sync status to job status hint for the job service
    if result.status == SyncStatus.FAILED:
        job_result["status"] = "failed"
    elif result.status == SyncStatus.PARTIAL and result.errors:
        job_result["status"] = "completed_with_errors"

    return job_result


def register_sync_jobs(job_service: JobService) -> None:
    """Register all sync job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.SYNC, sync_all_job)
    job_service.register_handler(JobType.SYNC_SCENES, sync_scenes_job)

    logger.info("Registered sync job handlers")
