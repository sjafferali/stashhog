"""Stash generate jobs for metadata generation."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models import Scene
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash import mutations, queries
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


# _handle_cancellation function removed - cancellation is now handled inline in _poll_job_status


async def _get_scenes_without_generated_attribute(
    db: AsyncSession, scene_ids: Optional[List[str]] = None
) -> List[str]:
    """Get scenes that don't have the generated attribute set.

    Args:
        db: Database session
        scene_ids: Optional list of specific scene IDs to check

    Returns:
        List of scene IDs that don't have generated=True
    """
    query = select(Scene.id).where(Scene.generated == False)  # noqa: E712

    # If specific scene IDs are provided, filter to those
    if scene_ids:
        query = query.where(Scene.id.in_(scene_ids))

    result = await db.execute(query)
    return [row[0] for row in result.fetchall()]


async def _update_scenes_generated_attribute(
    db: AsyncSession, scene_ids: List[str], generated: bool = True
) -> int:
    """Update the generated attribute for specified scenes.

    Args:
        db: Database session
        scene_ids: List of scene IDs to update
        generated: Value to set for the generated attribute

    Returns:
        Number of scenes updated
    """
    if not scene_ids:
        return 0

    stmt = update(Scene).where(Scene.id.in_(scene_ids)).values(generated=generated)
    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount


async def _update_progress_if_changed(
    progress: float,
    last_progress: float,
    description: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> float:
    """Update progress if it has changed."""
    if progress != last_progress:
        progress_int = int(progress * 100) if progress else 0
        await progress_callback(progress_int, f"Generate metadata: {description}")
        return progress
    return last_progress


def _process_job_status(
    job: Dict[str, Any], stash_job_id: str
) -> Optional[Dict[str, Any]]:
    """Process job status and return result if terminal state."""
    status = job.get("status", "").upper()

    if status == "FINISHED":
        return {
            "status": "completed",
            "message": "Metadata generation completed successfully",
            "stash_job_id": stash_job_id,
            "start_time": job.get("startTime"),
            "end_time": job.get("endTime"),
        }
    elif status == "FAILED":
        return {
            "status": "failed",
            "error": job.get("error") or "Metadata generation failed",
            "stash_job_id": stash_job_id,
        }
    elif status == "CANCELLED":
        return {
            "status": "cancelled",
            "message": "Metadata generation was cancelled",
            "stash_job_id": stash_job_id,
        }
    elif status == "STOPPING":
        logger.info(f"Stash job {stash_job_id} is stopping...")

    return None


async def _poll_job_status(
    stash_service: Any,
    stash_job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
) -> Dict[str, Any]:
    """Poll Stash job status until completion."""
    last_progress: float = 0
    poll_interval = 2  # seconds
    cancellation_requested = False

    while True:
        # If cancellation is requested but not yet sent to Stash
        if (
            cancellation_token
            and cancellation_token.is_cancelled
            and not cancellation_requested
        ):
            logger.info(f"Cancellation requested for Stash job {stash_job_id}")
            try:
                await stash_service.execute_graphql(
                    mutations.STOP_JOB, {"job_id": stash_job_id}
                )
                cancellation_requested = True
                logger.info(
                    f"Sent cancellation request to Stash for job {stash_job_id}"
                )
            except Exception as e:
                logger.error(f"Failed to stop Stash job {stash_job_id}: {e}")
                # Even if the stop request fails, mark as requested to avoid retrying
                cancellation_requested = True

        try:
            result = await stash_service.execute_graphql(
                queries.FIND_JOB, {"input": {"id": stash_job_id}}
            )

            job = result.get("findJob")
            if not job:
                logger.error(f"Job {stash_job_id} not found in Stash")
                return {
                    "status": "failed",
                    "error": f"Job {stash_job_id} not found in Stash",
                    "stash_job_id": stash_job_id,
                }

            progress = job.get("progress", 0)
            description = job.get("description", "")

            last_progress = await _update_progress_if_changed(
                progress, last_progress, description, progress_callback
            )

            job_result = _process_job_status(job, stash_job_id)
            if job_result:
                return job_result

            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error polling job status: {e}")
            await asyncio.sleep(poll_interval)


async def _prepare_generate_input(
    kwargs: Dict[str, Any], settings: Any
) -> Dict[str, Any]:
    """Prepare the input for metadata generation.

    Args:
        kwargs: Job parameters from metadata
        settings: Application settings

    Returns:
        Dictionary with generation input parameters
    """
    generate_input = {
        "covers": kwargs.get("covers", True),
        "sprites": kwargs.get("sprites", True),
        "previews": kwargs.get("previews", True),
        "imagePreviews": kwargs.get("imagePreviews", False),
        "markers": kwargs.get("markers", True),
        "markerImagePreviews": kwargs.get("markerImagePreviews", False),
        "markerScreenshots": kwargs.get("markerScreenshots", True),
        "transcodes": kwargs.get("transcodes", False),
        "forceTranscodes": kwargs.get("forceTranscodes", False),
        "phashes": kwargs.get("phashes", True),
        "interactiveHeatmapsSpeeds": kwargs.get("interactiveHeatmapsSpeeds", False),
        "clipPreviews": kwargs.get("clipPreviews", True),
        "imageThumbnails": kwargs.get("imageThumbnails", True),
        "overwrite": kwargs.get("overwrite", False),
    }

    # Add preview options if provided
    preview_options = kwargs.get("previewOptions", {})
    if preview_options:
        generate_input["previewOptions"] = {
            "previewSegments": preview_options.get("previewSegments", 12),
            "previewSegmentDuration": preview_options.get(
                "previewSegmentDuration", 0.75
            ),
            "previewExcludeStart": preview_options.get("previewExcludeStart", "0"),
            "previewExcludeEnd": preview_options.get("previewExcludeEnd", "0"),
            "previewPreset": preview_options.get(
                "previewPreset", settings.stash.preview_preset
            ),
        }
    else:
        # Use default preview options with configured preset
        generate_input["previewOptions"] = {
            "previewSegments": 12,
            "previewSegmentDuration": 0.75,
            "previewExcludeStart": "0",
            "previewExcludeEnd": "0",
            "previewPreset": settings.stash.preview_preset,
        }

    # Add scene IDs if provided
    scene_ids = kwargs.get("sceneIDs", [])
    if scene_ids:
        generate_input["sceneIDs"] = scene_ids

    # Add marker IDs if provided
    marker_ids = kwargs.get("markerIDs", [])
    if marker_ids:
        generate_input["markerIDs"] = marker_ids

    return generate_input


async def _handle_job_completion(
    final_status: str,
    scenes_to_update: List[str],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> int:
    """Handle job completion and update scene attributes.

    Args:
        final_status: The final status of the job
        scenes_to_update: List of scene IDs to update
        progress_callback: Async callback for progress updates

    Returns:
        Number of scenes updated
    """
    scenes_updated_count = 0

    if final_status == "completed" and scenes_to_update:
        await progress_callback(
            95, f"Updating generated attribute for {len(scenes_to_update)} scenes"
        )

        async with AsyncSessionLocal() as db:
            scenes_updated_count = await _update_scenes_generated_attribute(
                db, scenes_to_update, generated=True
            )

        logger.info(f"Updated generated attribute for {scenes_updated_count} scenes")
        await progress_callback(
            100,
            f"Metadata generation completed, updated {scenes_updated_count} scenes",
        )
    elif final_status == "cancelled":
        logger.info("Job was cancelled, not updating generated attribute")
        await progress_callback(100, "Metadata generation cancelled")
    elif final_status == "failed":
        logger.warning("Job failed, not updating generated attribute")
        await progress_callback(100, "Metadata generation failed")
    else:
        await progress_callback(100, f"Metadata generation {final_status}")

    return scenes_updated_count


async def stash_generate_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute a Stash metadata generation job.

    This job:
    1. Tracks scenes without the 'generated' attribute before starting
    2. Runs Stash metadata generation
    3. Updates the 'generated' attribute for all tracked scenes on successful completion
    """
    logger.info(f"Starting Stash generate job {job_id}")

    # Track scenes that will be impacted
    scenes_to_update: List[str] = []
    scenes_updated_count = 0

    try:
        # Initial progress
        await progress_callback(0, "Starting metadata generation")

        # Initialize services following the pattern from sync_jobs
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )

        # Get scene IDs from kwargs if provided
        scene_ids = kwargs.get("sceneIDs", [])

        # Track scenes that don't have the generated attribute set
        # This happens BEFORE we start the generation job
        async with AsyncSessionLocal() as db:
            if scene_ids:
                # If specific scenes are provided, check which ones need the attribute set
                scenes_to_update = await _get_scenes_without_generated_attribute(
                    db, scene_ids
                )
                logger.info(
                    f"Found {len(scenes_to_update)} scenes (out of {len(scene_ids)}) without generated attribute"
                )
            else:
                # If no specific scenes, we're generating for ALL scenes
                # Get all scenes that don't have generated=True
                scenes_to_update = await _get_scenes_without_generated_attribute(db)
                logger.info(
                    f"Found {len(scenes_to_update)} scenes without generated attribute"
                )

        await progress_callback(2, f"Tracked {len(scenes_to_update)} scenes for update")

        # Prepare generate input with default settings
        generate_input = await _prepare_generate_input(kwargs, settings)

        logger.info(f"Starting metadata generation with input: {generate_input}")
        await progress_callback(5, "Triggering metadata generation in Stash")

        # Execute metadata generate mutation
        result = await stash_service.execute_graphql(
            mutations.METADATA_GENERATE, {"input": generate_input}
        )

        stash_job_id = result.get("metadataGenerate")
        if not stash_job_id:
            raise Exception("Failed to start metadata generation - no job ID returned")

        logger.info(f"Started Stash job {stash_job_id}")
        await progress_callback(10, f"Stash job started: {stash_job_id}")

        # Poll job status until completion
        poll_result = await _poll_job_status(
            stash_service, stash_job_id, progress_callback, cancellation_token
        )

        # Final status handling
        final_status = poll_result.get("status", "completed")

        # Handle job completion and update scenes if successful
        scenes_updated_count = await _handle_job_completion(
            final_status, scenes_to_update, progress_callback
        )

        # Return enhanced result with scene information
        return {
            "job_id": job_id,
            "stash_job_id": stash_job_id,
            "scenes_updated_count": scenes_updated_count,
            "scenes_updated": scenes_to_update if scenes_updated_count > 0 else [],
            **poll_result,
        }

    except Exception as e:
        error_msg = f"Stash generate job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Don't update progress in error handler - let job service handle it
        raise
    finally:
        # Close Stash service connection
        if "stash_service" in locals():
            await stash_service.close()


def register_stash_generate_jobs(job_service: JobService) -> None:
    """Register Stash generate job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.STASH_GENERATE, stash_generate_job)

    logger.info("Registered Stash generate job handlers")
