"""Check Stash for resources requiring generation."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from app.core.settings_loader import load_settings_with_db_overrides
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


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

    # Check first batch of scenes for detailed missing content
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
            _process_scene_generation(scene, result)

        scenes_checked += len(scenes)
        progress = 30 + int((scenes_checked / total_scenes) * 40)
        await progress_callback(
            progress, f"Checked {scenes_checked}/{total_scenes} scenes"
        )

        # Break if we've checked enough scenes (sample check)
        if scenes_checked >= 5000:  # Limit detailed check to first 5000 scenes
            logger.info(f"Sampled {scenes_checked} scenes for detailed check")
            break

        page += 1


def _process_scene_generation(scene: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Process a single scene for missing generated content."""
    paths = scene.get("paths", {})
    details = cast(Dict[str, int], result["details"])
    sample_resources = cast(
        Dict[str, List[Dict[str, Any]]], result["sample_missing_resources"]
    )

    # Check for missing generated content
    if not paths.get("sprite"):
        details["scenes_missing_sprites"] += 1
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


async def _check_markers_with_plugin(
    stash_service: StashService,
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Check markers using plugin operation."""
    await progress_callback(70, "Checking markers for missing generated content")
    details = cast(Dict[str, int], result["details"])

    try:
        marker_check_response = await stash_service.execute_graphql(
            RUN_MARKER_CHECK_PLUGIN
        )
        plugin_result = marker_check_response.get("runPluginOperation", {})

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

    # Get sample of scenes missing covers if any
    if details["scenes_missing_cover"] > 0:
        await progress_callback(80, "Getting sample of scenes missing covers")
        cover_data = await stash_service.execute_graphql(SCENES_WITHOUT_COVER_QUERY)
        sample_scenes = cover_data.get("findScenes", {}).get("scenes", [])[:5]
        sample_resources["covers"] = [
            {"id": s["id"], "title": s.get("title", "Untitled")} for s in sample_scenes
        ]

    # Get sample of scenes missing phash if any
    if details["scenes_missing_phash"] > 0:
        await progress_callback(90, "Getting sample of scenes missing phash")
        phash_data = await stash_service.execute_graphql(SCENES_WITHOUT_PHASH_QUERY)
        sample_scenes = phash_data.get("findScenes", {}).get("scenes", [])[:5]
        sample_resources["phash"] = [
            {"id": s["id"], "title": s.get("title", "Untitled")} for s in sample_scenes
        ]


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

        result: Dict[str, Any] = {
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
        }

        # Check for cancellation
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Job {job_id} cancelled")
            return {"status": "cancelled", "job_id": job_id}

        # 1. Get overview counts
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
        if (
            details["scenes_missing_sprites"] > 0
            or details["scenes_missing_previews"] > 0
            or details["scenes_missing_webp"] > 0
            or details["markers_missing_video"] > 0
            or details["markers_missing_screenshot"] > 0
            or details["markers_missing_webp"] > 0
        ):
            result["resources_requiring_generation"] = True

        # 5. Get sample of missing resources
        await _get_sample_missing_resources(stash_service, result, progress_callback)

        # Final progress
        await progress_callback(100, "Check completed")

        # Log summary
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
