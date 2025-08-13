"""Remove orphaned entities job.

This job removes scenes, tags, performers, and studios from StashHog
that no longer exist in Stash.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models import Performer, Scene, Studio, Tag
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


async def _process_entity_removal(
    entity_type: str,
    db: AsyncSession,
    stash_service: StashService,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    dry_run: bool,
    remove_func: Callable,
) -> Dict[str, Any]:
    """Helper to process entity removal with error handling."""
    try:
        removed_count = await remove_func(
            db, stash_service, progress_callback, cancellation_token, dry_run
        )
        return {"removed": removed_count, "error": None}
    except Exception as e:
        logger.error(f"Error removing orphaned {entity_type}: {str(e)}")
        return {"removed": 0, "error": {"entity": entity_type, "error": str(e)}}


async def _update_progress(
    current_step: int,
    total_steps: int,
    message: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Helper to update progress."""
    progress = int((current_step / total_steps) * 100) if total_steps > 0 else 0
    await progress_callback(progress, message)


async def remove_orphaned_entities(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    remove_scenes: bool = True,
    remove_performers: bool = True,
    remove_tags: bool = True,
    remove_studios: bool = True,
    dry_run: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Remove entities from StashHog that no longer exist in Stash.

    This job will:
    1. Fetch all entity IDs from Stash
    2. Compare with entities in StashHog database
    3. Remove entities that exist in StashHog but not in Stash

    Args:
        job_id: Unique job identifier
        progress_callback: Async callback for progress updates
        cancellation_token: Token to check for job cancellation
        remove_scenes: Whether to remove orphaned scenes
        remove_performers: Whether to remove orphaned performers
        remove_tags: Whether to remove orphaned tags
        remove_studios: Whether to remove orphaned studios
        dry_run: If True, only report what would be deleted without actually deleting
        **kwargs: Additional job parameters

    Returns:
        Dictionary with job results including counts of removed entities
    """
    logger.info(f"Starting remove orphaned entities job {job_id}")
    logger.info(
        f"Options: scenes={remove_scenes}, performers={remove_performers}, "
        f"tags={remove_tags}, studios={remove_studios}, dry_run={dry_run}"
    )

    try:
        # Initial progress
        await progress_callback(0, "Initializing removal of orphaned entities...")

        # Initialize services
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )

        # Execute removal operations
        result = await _execute_removals(
            job_id,
            stash_service,
            progress_callback,
            cancellation_token,
            remove_scenes,
            remove_performers,
            remove_tags,
            remove_studios,
            dry_run,
        )

        return result

    except Exception as e:
        logger.error(f"Remove orphaned entities job failed: {str(e)}", exc_info=True)
        raise


async def _execute_removals(
    job_id: str,
    stash_service: StashService,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    remove_scenes: bool,
    remove_performers: bool,
    remove_tags: bool,
    remove_studios: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    """Execute the actual removal operations."""
    # Track results with proper typing
    results: Dict[str, Any] = {
        "scenes_removed": 0,
        "performers_removed": 0,
        "tags_removed": 0,
        "studios_removed": 0,
        "errors": [],
    }

    # Define removal operations
    operations = [
        (remove_scenes, "scenes", _remove_orphaned_scenes),
        (remove_performers, "performers", _remove_orphaned_performers),
        (remove_tags, "tags", _remove_orphaned_tags),
        (remove_studios, "studios", _remove_orphaned_studios),
    ]

    # Calculate total steps for progress
    active_operations = [op for op in operations if op[0]]
    total_steps = len(active_operations)

    async with AsyncSessionLocal() as db:
        # Check for cancellation
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Job {job_id} cancelled")
            return {"status": "cancelled", "job_id": job_id}

        # Process each entity type
        for idx, (should_remove, entity_type, remove_func) in enumerate(
            active_operations
        ):
            await _update_progress(
                idx,
                total_steps,
                f"Checking for orphaned {entity_type}...",
                progress_callback,
            )

            result = await _process_entity_removal(
                entity_type,
                db,
                stash_service,
                progress_callback,
                cancellation_token,
                dry_run,
                remove_func,
            )

            results[f"{entity_type}_removed"] = result["removed"]
            if result["error"]:
                errors_list: List[Dict[str, str]] = results["errors"]
                errors_list.append(result["error"])

        # Commit changes if not dry run
        if not dry_run:
            await db.commit()
            logger.info("Database changes committed")
        else:
            logger.info("Dry run - no changes committed")

    # Final progress
    total_removed = sum(
        [
            int(results["scenes_removed"]),
            int(results["performers_removed"]),
            int(results["tags_removed"]),
            int(results["studios_removed"]),
        ]
    )

    mode_text = " (DRY RUN)" if dry_run else ""
    await progress_callback(
        100, f"Completed{mode_text}: Removed {total_removed} orphaned entities"
    )

    return {
        "job_id": job_id,
        "status": "completed_with_errors" if results["errors"] else "completed",
        "dry_run": dry_run,
        "total_removed": total_removed,
        **results,
    }


async def _fetch_stash_scene_ids(
    stash_service: StashService, cancellation_token: Optional[Any]
) -> Set[str]:
    """Fetch all scene IDs from Stash."""
    stash_scene_ids: Set[str] = set()
    page = 1
    per_page = 1000

    while True:
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info("Job cancelled during scene fetch")
            return stash_scene_ids

        scenes, total = await stash_service.get_scenes(page=page, per_page=per_page)
        if not scenes:
            break

        stash_scene_ids.update(scene["id"] for scene in scenes)

        if len(scenes) < per_page:
            break
        page += 1

    return stash_scene_ids


async def _get_db_entity_ids(db: AsyncSession, model_class: Any) -> Set[str]:
    """Get all entity IDs from the database."""
    stmt = select(model_class.id)
    result = await db.execute(stmt)
    return {row[0] for row in result}


async def _remove_entities_by_ids(
    db: AsyncSession,
    model_class: Any,
    entity_ids: Set[str],
    entity_name: str,
    cancellation_token: Optional[Any],
) -> int:
    """Remove entities by their IDs."""
    removed_count = 0
    for entity_id in entity_ids:
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Job cancelled during {entity_name} removal")
            break

        try:
            stmt = select(model_class).where(model_class.id == entity_id)
            result = await db.execute(stmt)
            entity = result.scalar_one_or_none()

            if entity:
                await db.delete(entity)
                removed_count += 1
                logger.debug(f"Removed orphaned {entity_name}: {entity_id}")
        except Exception as e:
            logger.error(f"Error removing {entity_name} {entity_id}: {str(e)}")

    return removed_count


async def _remove_orphaned_scenes(
    db: AsyncSession,
    stash_service: StashService,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    dry_run: bool,
) -> int:
    """Remove scenes that no longer exist in Stash."""
    logger.info("Fetching all scene IDs from Stash...")

    # Get all scene IDs from Stash
    stash_scene_ids = await _fetch_stash_scene_ids(stash_service, cancellation_token)
    logger.info(f"Found {len(stash_scene_ids)} scenes in Stash")

    # Get all scene IDs from StashHog
    db_scene_ids = await _get_db_entity_ids(db, Scene)
    logger.info(f"Found {len(db_scene_ids)} scenes in StashHog")

    # Find orphaned scenes
    orphaned_scene_ids = db_scene_ids - stash_scene_ids

    if not orphaned_scene_ids:
        logger.info("No orphaned scenes found")
        return 0

    logger.info(f"Found {len(orphaned_scene_ids)} orphaned scenes")

    if dry_run:
        logger.info(f"DRY RUN: Would remove {len(orphaned_scene_ids)} scenes")
        for scene_id in list(orphaned_scene_ids)[:10]:  # Log first 10
            logger.info(f"  - Scene ID: {scene_id}")
        if len(orphaned_scene_ids) > 10:
            logger.info(f"  ... and {len(orphaned_scene_ids) - 10} more")
        return len(orphaned_scene_ids)

    # Remove orphaned scenes
    removed_count = await _remove_entities_by_ids(
        db, Scene, orphaned_scene_ids, "scene", cancellation_token
    )

    logger.info(f"Removed {removed_count} orphaned scenes")
    return removed_count


async def _remove_orphaned_performers(
    db: AsyncSession,
    stash_service: StashService,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    dry_run: bool,
) -> int:
    """Remove performers that no longer exist in Stash."""
    logger.info("Fetching all performer IDs from Stash...")

    # Get all performers from Stash
    stash_performers = await stash_service.get_all_performers()
    stash_performer_ids = {p["id"] for p in stash_performers}
    logger.info(f"Found {len(stash_performer_ids)} performers in Stash")

    # Get all performer IDs from StashHog
    db_performer_ids = await _get_db_entity_ids(db, Performer)
    logger.info(f"Found {len(db_performer_ids)} performers in StashHog")

    # Find orphaned performers
    orphaned_performer_ids = db_performer_ids - stash_performer_ids

    if not orphaned_performer_ids:
        logger.info("No orphaned performers found")
        return 0

    logger.info(f"Found {len(orphaned_performer_ids)} orphaned performers")

    if dry_run:
        logger.info(f"DRY RUN: Would remove {len(orphaned_performer_ids)} performers")
        return len(orphaned_performer_ids)

    # Remove orphaned performers
    removed_count = await _remove_entities_by_ids(
        db, Performer, orphaned_performer_ids, "performer", cancellation_token
    )

    logger.info(f"Removed {removed_count} orphaned performers")
    return removed_count


async def _remove_orphaned_tags(
    db: AsyncSession,
    stash_service: StashService,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    dry_run: bool,
) -> int:
    """Remove tags that no longer exist in Stash."""
    logger.info("Fetching all tag IDs from Stash...")

    # Get all tags from Stash
    stash_tags = await stash_service.get_all_tags()
    stash_tag_ids = {t["id"] for t in stash_tags}
    logger.info(f"Found {len(stash_tag_ids)} tags in Stash")

    # Get all tag IDs from StashHog
    db_tag_ids = await _get_db_entity_ids(db, Tag)
    logger.info(f"Found {len(db_tag_ids)} tags in StashHog")

    # Find orphaned tags
    orphaned_tag_ids = db_tag_ids - stash_tag_ids

    if not orphaned_tag_ids:
        logger.info("No orphaned tags found")
        return 0

    logger.info(f"Found {len(orphaned_tag_ids)} orphaned tags")

    if dry_run:
        logger.info(f"DRY RUN: Would remove {len(orphaned_tag_ids)} tags")
        return len(orphaned_tag_ids)

    # Remove orphaned tags
    removed_count = await _remove_entities_by_ids(
        db, Tag, orphaned_tag_ids, "tag", cancellation_token
    )

    logger.info(f"Removed {removed_count} orphaned tags")
    return removed_count


async def _remove_orphaned_studios(
    db: AsyncSession,
    stash_service: StashService,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    dry_run: bool,
) -> int:
    """Remove studios that no longer exist in Stash."""
    logger.info("Fetching all studio IDs from Stash...")

    # Get all studios from Stash
    stash_studios = await stash_service.get_all_studios()
    stash_studio_ids = {s["id"] for s in stash_studios}
    logger.info(f"Found {len(stash_studio_ids)} studios in Stash")

    # Get all studio IDs from StashHog
    db_studio_ids = await _get_db_entity_ids(db, Studio)
    logger.info(f"Found {len(db_studio_ids)} studios in StashHog")

    # Find orphaned studios
    orphaned_studio_ids = db_studio_ids - stash_studio_ids

    if not orphaned_studio_ids:
        logger.info("No orphaned studios found")
        return 0

    logger.info(f"Found {len(orphaned_studio_ids)} orphaned studios")

    if dry_run:
        logger.info(f"DRY RUN: Would remove {len(orphaned_studio_ids)} studios")
        return len(orphaned_studio_ids)

    # Remove orphaned studios
    removed_count = await _remove_entities_by_ids(
        db, Studio, orphaned_studio_ids, "studio", cancellation_token
    )

    logger.info(f"Removed {removed_count} orphaned studios")
    return removed_count


def register_remove_orphaned_entities_jobs(job_service: JobService) -> None:
    """Register remove orphaned entities job handler.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(
        JobType.REMOVE_ORPHANED_ENTITIES, remove_orphaned_entities
    )
    logger.info("Registered remove orphaned entities job handler")
