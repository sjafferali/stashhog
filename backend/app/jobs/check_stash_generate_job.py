"""Check Stash for resources requiring generation."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models import Scene
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


async def _update_scenes_generated_attribute(
    db: AsyncSession,
    scenes_needing_generation: Set[str],
    all_scene_ids: List[str],
) -> Dict[str, int]:
    """Update the generated attribute for scenes based on resource check results.

    Args:
        db: Database session
        scenes_needing_generation: Set of scene IDs that need generation (will be marked as generated=false)
        all_scene_ids: List of all scene IDs that were checked

    Returns:
        Dictionary with counts of scenes marked as generated and not generated
    """
    scenes_marked_generated = 0
    scenes_marked_not_generated = 0

    # Convert set to list for SQL IN clause
    scenes_needing_generation_list = list(scenes_needing_generation)

    # Mark scenes that need generation as generated=false
    if scenes_needing_generation_list:
        stmt = (
            update(Scene)
            .where(Scene.id.in_(scenes_needing_generation_list))
            .values(generated=False)
        )
        result = await db.execute(stmt)
        scenes_marked_not_generated = result.rowcount
        logger.info(f"Marked {scenes_marked_not_generated} scenes as generated=false")

    # Mark scenes that don't need generation as generated=true
    # Only update scenes that exist in our database
    scenes_fully_generated = [
        scene_id
        for scene_id in all_scene_ids
        if scene_id not in scenes_needing_generation
    ]

    if scenes_fully_generated:
        # First check which scenes exist in our database
        existing_query = select(Scene.id).where(Scene.id.in_(scenes_fully_generated))
        existing_result = await db.execute(existing_query)
        existing_scene_ids = [row[0] for row in existing_result.fetchall()]

        if existing_scene_ids:
            stmt = (
                update(Scene)
                .where(Scene.id.in_(existing_scene_ids))
                .values(generated=True)
            )
            result = await db.execute(stmt)
            scenes_marked_generated = result.rowcount
            logger.info(f"Marked {scenes_marked_generated} scenes as generated=true")

    await db.commit()

    return {
        "scenes_marked_generated": scenes_marked_generated,
        "scenes_marked_not_generated": scenes_marked_not_generated,
    }


SCENES_WITHOUT_COVER_QUERY = """
query ScenesWithoutCover {
  findScenes(
    scene_filter: {
      is_missing: "cover"
    }
    filter: {
      per_page: -1
    }
  ) {
    count
    scenes {
      id
      title
    }
  }
}
"""

SCENES_WITHOUT_PHASH_QUERY = """
query ScenesWithoutPhash {
  findScenes(
    scene_filter: {
      is_missing: "phash"
    }
    filter: {
      per_page: -1
    }
  ) {
    count
    scenes {
      id
      title
    }
  }
}
"""

CHECK_SCENE_GENERATION_QUERY = """
query CheckSceneGeneration($page: Int!, $per_page: Int!) {
  findScenes(
    filter: {
      per_page: $per_page
      page: $page
    }
  ) {
    count
    scenes {
      id
      title
      paths {
        screenshot
        preview
        webp
        sprite
        vtt
      }
    }
  }
}
"""

RUN_MARKER_CHECK_PLUGIN = """
mutation RunPluginOperation {
  runPluginOperation(
    plugin_id: "marker_check"
    args: {
      mode: "check"
    }
  )
}
"""

PENDING_GENERATION_QUERY = """
query PendingGeneration {
  allScenes: findScenes(filter: { per_page: 0 }) {
    count
  }

  missingCovers: findScenes(
    scene_filter: { is_missing: "cover" }
    filter: { per_page: 0 }
  ) {
    count
  }

  missingPhash: findScenes(
    scene_filter: { is_missing: "phash" }
    filter: { per_page: 0 }
  ) {
    count
  }
}
"""


async def _check_scene_generation_details(
    stash_service: StashService,
    result: Dict[str, Any],
    cancellation_token: Optional[Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Check scenes for missing sprites/previews."""
    details = cast(Dict[str, int], result["details"])
    total_scenes = details["total_scenes"]
    if total_scenes == 0:
        return

    # Initialize tracking sets for scene generation status
    all_scene_ids = cast(List[str], result.get("all_scene_ids", []))

    # Check ALL scenes for detailed missing content (not just a sample)
    per_page = min(1000, total_scenes)  # Limit to 1000 per batch
    page = 1
    scenes_checked = 0

    while scenes_checked < total_scenes:
        if cancellation_token and cancellation_token.is_cancelled:
            raise Exception("Job cancelled")

        scene_data = await stash_service.execute_graphql(
            CHECK_SCENE_GENERATION_QUERY, {"page": page, "per_page": per_page}
        )

        scenes = scene_data.get("findScenes", {}).get("scenes", [])

        for scene in scenes:
            # Track all scene IDs
            all_scene_ids.append(scene["id"])
            _process_scene_generation(scene, result)

        scenes_checked += len(scenes)
        progress = 30 + int((scenes_checked / total_scenes) * 40)
        await progress_callback(
            progress, f"Checked {scenes_checked}/{total_scenes} scenes"
        )

        # Continue until all scenes are checked
        if len(scenes) < per_page:  # No more scenes to check
            break

        page += 1

    # Store all scene IDs in result
    result["all_scene_ids"] = all_scene_ids


def _process_scene_generation(scene: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Process a single scene for missing generated content."""
    paths = scene.get("paths", {})
    details = cast(Dict[str, int], result["details"])
    sample_resources = cast(
        Dict[str, List[Dict[str, Any]]], result["sample_missing_resources"]
    )
    scenes_needing_generation = cast(
        Set[str], result.get("scenes_needing_generation", set())
    )

    # Track if this scene needs generation
    scene_needs_generation = False

    # Check for missing generated content
    if not paths.get("sprite"):
        details["scenes_missing_sprites"] += 1
        scene_needs_generation = True
        sprites_list = cast(List[Dict[str, Any]], sample_resources["sprites"])
        if len(sprites_list) < 5:
            sprites_list.append(
                {
                    "id": scene["id"],
                    "title": scene.get("title", "Untitled"),
                }
            )

    if not paths.get("preview"):
        details["scenes_missing_previews"] += 1
        scene_needs_generation = True
        previews_list = cast(List[Dict[str, Any]], sample_resources["previews"])
        if len(previews_list) < 5:
            previews_list.append(
                {
                    "id": scene["id"],
                    "title": scene.get("title", "Untitled"),
                }
            )

    if not paths.get("webp"):
        details["scenes_missing_webp"] += 1
        scene_needs_generation = True

    # Also check for missing cover (screenshot) and vtt
    if not paths.get("screenshot"):
        scene_needs_generation = True

    if not paths.get("vtt"):
        scene_needs_generation = True

    # Add scene to tracking set if it needs generation
    if scene_needs_generation:
        scenes_needing_generation.add(scene["id"])

    result["scenes_needing_generation"] = scenes_needing_generation


async def _check_markers_with_plugin(
    stash_service: StashService,
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Check markers using plugin operation."""
    await progress_callback(70, "Checking markers for missing generated content")
    details = cast(Dict[str, int], result["details"])
    scenes_needing_generation = cast(
        Set[str], result.get("scenes_needing_generation", set())
    )

    try:
        # Use 10-minute timeout for marker check plugin as it checks every marker
        marker_check_response = await stash_service.execute_graphql(
            RUN_MARKER_CHECK_PLUGIN, timeout=600
        )
        # The execute_graphql method already extracts the data portion
        plugin_result = marker_check_response.get("runPluginOperation", {})

        # Log the plugin response for debugging
        logger.info(
            f"Marker check plugin response: total_markers={plugin_result.get('total_markers', 0)}, "
            f"markers_needing_video_count={plugin_result.get('markers_needing_video_count', 0)}, "
            f"markers_needing_screenshot_count={plugin_result.get('markers_needing_screenshot_count', 0)}, "
            f"markers_needing_webp_count={plugin_result.get('markers_needing_webp_count', 0)}"
        )

        # Update marker statistics from plugin response
        details["total_markers"] = plugin_result.get("total_markers", 0)
        details["markers_missing_video"] = plugin_result.get(
            "markers_needing_video_count", 0
        )
        details["markers_missing_screenshot"] = plugin_result.get(
            "markers_needing_screenshot_count", 0
        )
        details["markers_missing_webp"] = plugin_result.get(
            "markers_needing_webp_count", 0
        )

        # Store marker IDs that need generation
        result["markers_needing_generation"] = plugin_result.get(
            "markers_needing_generation", []
        )
        result["markers_needing_generation_count"] = plugin_result.get(
            "markers_needing_generation_count", 0
        )

        # Track scenes that have markers needing generation
        markers_by_scene = plugin_result.get("markers_by_scene", {})
        for scene_id, marker_info in markers_by_scene.items():
            if marker_info.get("needs_generation", False):
                scenes_needing_generation.add(scene_id)

        result["scenes_needing_generation"] = scenes_needing_generation

        # Get sample marker videos if any are missing
        if details["markers_missing_video"] > 0:
            sample_marker_ids = plugin_result.get("markers_needing_video", [])[:5]
            sample_resources = cast(
                Dict[str, List[Dict[str, Any]]], result["sample_missing_resources"]
            )
            sample_resources["marker_videos"] = [
                {"marker_id": marker_id} for marker_id in sample_marker_ids
            ]

    except Exception as e:
        logger.error(f"Error running marker check plugin: {e}")
        # Continue without marker data rather than failing the job
        details["markers_missing_video"] = 0
        details["markers_missing_screenshot"] = 0
        details["markers_missing_webp"] = 0


async def _get_sample_missing_resources(
    stash_service: StashService,
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Get samples of missing resources."""
    details = cast(Dict[str, int], result["details"])
    sample_resources = cast(
        Dict[str, List[Dict[str, Any]]], result["sample_missing_resources"]
    )
    scenes_needing_generation = cast(
        Set[str], result.get("scenes_needing_generation", set())
    )

    # Get sample of scenes missing covers if any
    if details["scenes_missing_cover"] > 0:
        await progress_callback(80, "Getting sample of scenes missing covers")
        cover_data = await stash_service.execute_graphql(SCENES_WITHOUT_COVER_QUERY)
        sample_scenes = cover_data.get("findScenes", {}).get("scenes", [])[:5]
        sample_resources["covers"] = [
            {"id": s["id"], "title": s.get("title", "Untitled")} for s in sample_scenes
        ]
        # Add all scenes missing covers to the tracking set
        all_scenes_missing_covers = cover_data.get("findScenes", {}).get("scenes", [])
        for scene in all_scenes_missing_covers:
            scenes_needing_generation.add(scene["id"])

    # Get sample of scenes missing phash if any
    if details["scenes_missing_phash"] > 0:
        await progress_callback(90, "Getting sample of scenes missing phash")
        phash_data = await stash_service.execute_graphql(SCENES_WITHOUT_PHASH_QUERY)
        sample_scenes = phash_data.get("findScenes", {}).get("scenes", [])[:5]
        sample_resources["phash"] = [
            {"id": s["id"], "title": s.get("title", "Untitled")} for s in sample_scenes
        ]
        # Add all scenes missing phash to the tracking set
        all_scenes_missing_phash = phash_data.get("findScenes", {}).get("scenes", [])
        for scene in all_scenes_missing_phash:
            scenes_needing_generation.add(scene["id"])

    result["scenes_needing_generation"] = scenes_needing_generation


async def _initialize_result(job_id: str) -> Dict[str, Any]:
    """Initialize the result dictionary for the job."""
    return {
        "job_id": job_id,
        "status": "completed",
        "resources_requiring_generation": False,
        "details": {
            "scenes_missing_cover": 0,
            "scenes_missing_phash": 0,
            "scenes_missing_sprites": 0,
            "scenes_missing_previews": 0,
            "scenes_missing_webp": 0,
            "markers_missing_video": 0,
            "markers_missing_screenshot": 0,
            "markers_missing_webp": 0,
            "total_scenes": 0,
            "total_markers": 0,
        },
        "sample_missing_resources": {
            "covers": [],
            "phash": [],
            "sprites": [],
            "previews": [],
            "marker_videos": [],
        },
        "all_scene_ids": [],  # Track all scene IDs that were checked
    }


async def _check_overview_counts(
    stash_service: StashService,
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Check overview counts and update result."""
    await progress_callback(10, "Fetching overview statistics")
    overview_data = await stash_service.execute_graphql(PENDING_GENERATION_QUERY)

    details = cast(Dict[str, int], result["details"])
    details["total_scenes"] = overview_data.get("allScenes", {}).get("count", 0)
    details["scenes_missing_cover"] = overview_data.get("missingCovers", {}).get(
        "count", 0
    )
    details["scenes_missing_phash"] = overview_data.get("missingPhash", {}).get(
        "count", 0
    )

    # Check if any basic resources are missing
    if details["scenes_missing_cover"] > 0 or details["scenes_missing_phash"] > 0:
        result["resources_requiring_generation"] = True


def _check_missing_generated_content(result: Dict[str, Any]) -> None:
    """Check if any generated content is missing and update result."""
    details = cast(Dict[str, int], result["details"])
    if (
        details["scenes_missing_sprites"] > 0
        or details["scenes_missing_previews"] > 0
        or details["scenes_missing_webp"] > 0
        or details["markers_missing_video"] > 0
        or details["markers_missing_screenshot"] > 0
        or details["markers_missing_webp"] > 0
    ):
        result["resources_requiring_generation"] = True


async def _finalize_result(
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Finalize the result and update database."""
    # Convert the set to a list for JSON serialization
    scenes_needing_generation_set = result.get("scenes_needing_generation", set())
    result["scenes_needing_generation"] = list(scenes_needing_generation_set)
    result["scenes_needing_generation_count"] = len(result["scenes_needing_generation"])

    # Update the generated attribute in the database
    await progress_callback(95, "Updating scene generation status")

    async with AsyncSessionLocal() as db:
        try:
            all_scene_ids = result.get("all_scene_ids", [])
            update_results = await _update_scenes_generated_attribute(
                db, scenes_needing_generation_set, all_scene_ids
            )

            result["database_updates"] = update_results
            logger.info(
                f"Database update complete: "
                f"{update_results['scenes_marked_generated']} scenes marked as generated, "
                f"{update_results['scenes_marked_not_generated']} scenes marked as not generated"
            )
        except Exception as e:
            logger.error(f"Failed to update scene generated attributes: {e}")
            result["database_update_error"] = str(e)


async def check_stash_generate(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Check Stash for resources requiring generation.

    This job performs multiple queries to identify:
    1. Scenes missing covers
    2. Scenes missing phash
    3. Scenes missing sprites/previews
    4. Markers missing video/screenshot/webp (via plugin operation)

    Args:
        job_id: Unique job identifier
        progress_callback: Async callback for progress updates
        cancellation_token: Token to check for job cancellation
        **kwargs: Job parameters from metadata
    """
    logger.info(f"Starting check_stash_generate job {job_id}")

    try:
        # Initial progress
        await progress_callback(0, "Starting Stash generation check")

        # Initialize services
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )

        result = await _initialize_result(job_id)

        # Check for cancellation
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Job {job_id} cancelled")
            return {"status": "cancelled", "job_id": job_id}

        # 1. Get overview counts
        await _check_overview_counts(stash_service, result, progress_callback)

        # 2. Check scenes for missing sprites/previews (paginated)
        await progress_callback(30, "Checking scenes for missing generated content")

        try:
            await _check_scene_generation_details(
                stash_service, result, cancellation_token, progress_callback
            )
        except Exception as e:
            if "Job cancelled" in str(e):
                return {"status": "cancelled", "job_id": job_id}
            raise

        # 3. Check markers using plugin operation
        await _check_markers_with_plugin(stash_service, result, progress_callback)

        # 4. Check if we found any missing generated content
        _check_missing_generated_content(result)

        # 5. Get sample of missing resources
        await _get_sample_missing_resources(stash_service, result, progress_callback)

        # Final progress
        await progress_callback(100, "Check completed")

        # Log summary
        details = cast(Dict[str, int], result["details"])
        logger.info(
            f"Check complete: resources_requiring_generation={result['resources_requiring_generation']}"
        )
        logger.info(f"Missing covers: {details['scenes_missing_cover']}")
        logger.info(f"Missing phash: {details['scenes_missing_phash']}")
        logger.info(f"Missing sprites: {details['scenes_missing_sprites']}")
        logger.info(f"Missing previews: {details['scenes_missing_previews']}")
        logger.info(f"Missing marker videos: {details['markers_missing_video']}")
        logger.info(
            f"Missing marker screenshots: {details['markers_missing_screenshot']}"
        )
        logger.info(f"Missing marker webp: {details['markers_missing_webp']}")

        # Finalize result and update database
        await _finalize_result(result, progress_callback)

        return result

    except Exception as e:
        error_msg = f"Check Stash generation job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise
    finally:
        # Clean up service connection
        if "stash_service" in locals():
            await stash_service.close()


def register_check_stash_generate_jobs(job_service: JobService) -> None:
    """Register job handlers with the job service."""
    job_service.register_handler(JobType.CHECK_STASH_GENERATE, check_stash_generate)
    logger.info("Registered check_stash_generate job handler")
