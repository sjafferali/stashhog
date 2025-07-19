import logging
from typing import Any, Callable, Dict, List, Optional

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService
from app.services.sync.sync_service import SyncService

logger = logging.getLogger(__name__)


async def sync_all_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    force: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute full synchronization from Stash as a background job."""
    logger.info(f"Starting sync_all job {job_id} with force={force}")
    logger.debug(f"sync_all_job called with kwargs: {kwargs}")

    # Create services for this job
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url, api_key=settings.stash.api_key
    )
    async with AsyncSessionLocal() as db:
        logger.debug(f"Created database session: {type(db)}")
        sync_service = SyncService(stash_service, db)
        logger.debug("Created sync service instance")

        # Execute sync with progress callback
        try:
            logger.debug("About to call sync_service.sync_all")
            result = await sync_service.sync_all(
                job_id=job_id,
                force=force,
                progress_callback=progress_callback,
                cancellation_token=cancellation_token,
            )
            logger.debug(f"sync_all completed with status: {result.status}")
        except Exception as e:
            logger.error(f"sync_all_job failed: {str(e)}")
            logger.debug(f"sync_all_job exception type: {type(e).__name__}")
            logger.debug(f"sync_all_job exception value: {repr(e)}")
            logger.debug(
                f"sync_all_job exception args: {e.args if hasattr(e, 'args') else 'No args'}"
            )
            import traceback

            logger.debug(f"sync_all_job traceback:\n{traceback.format_exc()}")
            raise

    # Convert SyncResult dataclass to dict manually
    return {
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
    }


async def sync_scenes_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    scene_ids: Optional[List[str]] = None,
    force: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Sync specific scenes as a background job."""
    logger.info(f"Starting sync_scenes job {job_id} for {len(scene_ids or [])} scenes")

    # Create services for this job
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url, api_key=settings.stash.api_key
    )
    async with AsyncSessionLocal() as db:
        sync_service = SyncService(stash_service, db)

        # Execute sync with progress callback
        result = await sync_service.sync_scenes(
            scene_ids=scene_ids,
            job_id=job_id,
            force=force,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    # Convert SyncResult dataclass to dict manually
    return {
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
    }


async def sync_performers_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    force: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Sync performers as a background job."""
    logger.info(f"Starting sync_performers job {job_id}")

    # Create services for this job
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url, api_key=settings.stash.api_key
    )
    async with AsyncSessionLocal() as db:
        sync_service = SyncService(stash_service, db)

        # Execute sync with progress callback
        result = await sync_service.sync_performers(
            job_id=job_id, force=force, progress_callback=progress_callback
        )

    # Convert SyncResult dataclass to dict manually
    return {
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
    }


async def sync_tags_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    force: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Sync tags as a background job."""
    logger.info(f"Starting sync_tags job {job_id}")

    # Create services for this job
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url, api_key=settings.stash.api_key
    )
    async with AsyncSessionLocal() as db:
        sync_service = SyncService(stash_service, db)

        # Execute sync with progress callback
        result = await sync_service.sync_tags(
            job_id=job_id, force=force, progress_callback=progress_callback
        )

    # Convert SyncResult dataclass to dict manually
    return {
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
    }


async def sync_studios_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    force: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Sync studios as a background job."""
    logger.info(f"Starting sync_studios job {job_id}")

    # Create services for this job
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url, api_key=settings.stash.api_key
    )
    async with AsyncSessionLocal() as db:
        sync_service = SyncService(stash_service, db)

        # Execute sync with progress callback
        result = await sync_service.sync_studios(
            job_id=job_id, force=force, progress_callback=progress_callback
        )

    # Convert SyncResult dataclass to dict manually
    return {
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
    }


def register_sync_jobs(job_service: JobService) -> None:
    """Register all sync job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.SYNC, sync_all_job)
    job_service.register_handler(JobType.SYNC_SCENES, sync_scenes_job)
    job_service.register_handler(JobType.SYNC_PERFORMERS, sync_performers_job)
    job_service.register_handler(JobType.SYNC_TAGS, sync_tags_job)
    job_service.register_handler(JobType.SYNC_STUDIOS, sync_studios_job)

    logger.info("Registered all sync job handlers")
