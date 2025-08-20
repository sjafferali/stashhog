"""Local generate job for creating scene marker previews and screenshots."""

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from app.core.settings_loader import load_settings_with_db_overrides
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


async def generate_screenshot(
    video_path: str,
    output_path: str,
    seconds: float,
    width: int = 1280,
) -> bool:
    """Generate a screenshot from video at specified time.

    Args:
        video_path: Path to the video file
        output_path: Path where screenshot will be saved
        seconds: Time in seconds to capture screenshot
        width: Width of the screenshot (height will be calculated to maintain aspect ratio)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-ss",
            str(seconds),
            "-vf",
            f"scale={width}:-2",
            "-q:v",
            "2",
            "-frames:v",
            "1",
            "-y",  # Overwrite output file
            output_path,
        ]

        # Execute ffmpeg command
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg screenshot failed: {stderr.decode()}")
            return False

        return True

    except Exception as e:
        logger.error(f"Failed to generate screenshot: {e}")
        return False


async def generate_video_preview(
    video_path: str,
    output_path: str,
    start_seconds: float,
    duration: float,
    width: int = 640,
) -> bool:
    """Generate a video preview from source video.

    Args:
        video_path: Path to the video file
        output_path: Path where preview video will be saved
        start_seconds: Start time in seconds
        duration: Duration of the preview in seconds
        width: Width of the preview (height will be calculated to maintain aspect ratio)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-ss",
            str(start_seconds),
            "-t",
            str(duration),
            "-vf",
            f"scale={width}:-2",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-y",  # Overwrite output file
            output_path,
        ]

        # Execute ffmpeg command
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg video preview failed: {stderr.decode()}")
            return False

        return True

    except Exception as e:
        logger.error(f"Failed to generate video preview: {e}")
        return False


async def _process_marker(
    marker: Dict[str, Any],
    video_path: str,
    scene_hash: str,
    width: int,
    idx: int,
    total: int,
) -> Dict[str, int]:
    """Process a single marker.

    Returns:
        Dict with counts of generated and skipped files
    """
    seconds = marker.get("seconds", 0)
    end_seconds = marker.get("end_seconds")
    title = marker.get("title", f"Marker at {seconds}s")

    logger.info(f"LOCALGENERATE: Processing marker {idx + 1}/{total}: {title}")

    # Calculate duration for preview
    duration = min(end_seconds - seconds, 20) if end_seconds else 20

    # Generate output paths
    output_dir = f"/generated/markers/{scene_hash}"
    screenshot_path = f"{output_dir}/{seconds}.jpg"
    preview_path = f"{output_dir}/{seconds}.mp4"

    results = {
        "generated_screenshots": 0,
        "generated_previews": 0,
        "skipped_screenshots": 0,
        "skipped_previews": 0,
    }

    # Check and generate screenshot
    if os.path.exists(screenshot_path):
        logger.info(f"LOCALGENERATE: Screenshot already exists: {screenshot_path}")
        results["skipped_screenshots"] = 1
    else:
        logger.info(f"LOCALGENERATE: Generating screenshot: {screenshot_path}")
        if await generate_screenshot(video_path, screenshot_path, seconds, width):
            logger.info(
                f"LOCALGENERATE: Successfully generated screenshot: {screenshot_path}"
            )
            results["generated_screenshots"] = 1
        else:
            logger.error(
                f"LOCALGENERATE: Failed to generate screenshot: {screenshot_path}"
            )

    # Check and generate video preview
    if os.path.exists(preview_path):
        logger.info(f"LOCALGENERATE: Video preview already exists: {preview_path}")
        results["skipped_previews"] = 1
    else:
        logger.info(f"LOCALGENERATE: Generating video preview: {preview_path}")
        if await generate_video_preview(video_path, preview_path, seconds, duration):
            logger.info(
                f"LOCALGENERATE: Successfully generated video preview: {preview_path}"
            )
            results["generated_previews"] = 1
        else:
            logger.error(
                f"LOCALGENERATE: Failed to generate video preview: {preview_path}"
            )

    return results


async def _fetch_scene_data(
    stash_service: StashService, scene_id: str
) -> Dict[str, Any]:
    """Fetch scene data from Stash."""
    query = """
    query FindScenes($scene_ids: [Int!]) {
        findScenes(scene_ids: $scene_ids) {
            count
            scenes {
                id
                title
                urls
                paths {
                    screenshot
                    preview
                    stream
                    webp
                    vtt
                    sprite
                    funscript
                    interactive_heatmap
                    caption
                }
                interactive
                interactive_speed
                organized
                scene_markers {
                    id
                    created_at
                    updated_at
                    primary_tag {
                        id
                        name
                    }
                    seconds
                    end_seconds
                    tags {
                        id
                        name
                    }
                    title
                }
                details
                created_at
                updated_at
                date
                rating100
                studio {
                    id
                    name
                }
                performers {
                    id
                    name
                    gender
                    favorite
                    rating100
                }
                tags {
                    id
                    name
                }
                movies {
                    movie {
                        id
                        name
                    }
                    scene_index
                }
                galleries {
                    id
                    title
                    paths {
                        cover
                        preview
                    }
                }
                files {
                    path
                    size
                    id
                    duration
                    video_codec
                    audio_codec
                    width
                    height
                    frame_rate
                    fingerprints {
                        value
                        type
                    }
                    bit_rate
                }
                o_counter
            }
        }
    }
    """

    result = await stash_service.execute_graphql(query, {"scene_ids": [int(scene_id)]})

    find_scenes = result.get("findScenes", {})
    scenes = find_scenes.get("scenes", [])

    if not scenes:
        raise ValueError(f"Scene {scene_id} not found in Stash")

    scene_data: Dict[str, Any] = scenes[0]
    return scene_data


async def _validate_and_extract_file_info(
    scene: Dict[str, Any], scene_id: str
) -> Tuple[str, str]:
    """Validate scene has files and return video path and oshash.

    Returns:
        Tuple of (video_path, oshash)

    Raises:
        ValueError: If no files found, video file doesn't exist, or oshash not found
    """
    files = scene.get("files", [])
    if not files:
        raise ValueError(f"LOCALGENERATE: No files found for scene {scene_id}")

    file_info = files[0]
    video_path = file_info.get("path")
    if not video_path or not os.path.exists(video_path):
        raise ValueError(f"LOCALGENERATE: Video file not found: {video_path}")

    # Extract oshash from fingerprints
    fingerprints = file_info.get("fingerprints", [])
    oshash = None
    for fingerprint in fingerprints:
        if fingerprint.get("type") == "oshash":
            oshash = fingerprint.get("value")
            break

    if not oshash:
        raise ValueError(
            f"LOCALGENERATE: No oshash found in fingerprints for scene {scene_id}"
        )

    path: str = video_path
    hash_value: str = oshash
    return path, hash_value


async def _process_all_markers(
    scene_markers: list,
    video_path: str,
    scene_hash: str,
    width: int,
    job_id: str,
    cancellation_token: Optional[Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> Dict[str, int]:
    """Process all scene markers.

    Returns:
        Dict with generation statistics
    """
    total_markers = len(scene_markers)
    generated_screenshots = 0
    generated_previews = 0
    skipped_screenshots = 0
    skipped_previews = 0

    await progress_callback(20, f"LOCALGENERATE: Processing {total_markers} markers")

    for idx, marker in enumerate(scene_markers):
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"LOCALGENERATE: Job {job_id} cancelled")
            raise asyncio.CancelledError("Job cancelled")

        # Process the marker
        marker_results = await _process_marker(
            marker, video_path, scene_hash, width, idx, total_markers
        )

        # Update counters
        generated_screenshots += marker_results["generated_screenshots"]
        generated_previews += marker_results["generated_previews"]
        skipped_screenshots += marker_results["skipped_screenshots"]
        skipped_previews += marker_results["skipped_previews"]

        # Update progress
        progress = 20 + int((idx + 1) / total_markers * 70)
        await progress_callback(
            progress, f"LOCALGENERATE: Processed {idx + 1}/{total_markers} markers"
        )

    return {
        "total_markers": total_markers,
        "generated_screenshots": generated_screenshots,
        "generated_previews": generated_previews,
        "skipped_screenshots": skipped_screenshots,
        "skipped_previews": skipped_previews,
    }


async def local_generate_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute local generation for a single scene.

    Args:
        job_id: Unique job identifier
        progress_callback: Async callback for progress updates
        cancellation_token: Token to check for job cancellation
        **kwargs: Job parameters including 'scene_id'
    """
    logger.info(f"LOCALGENERATE: Starting local generate job {job_id}")

    # Get scene ID from kwargs
    scene_id = kwargs.get("scene_id")
    if not scene_id:
        error_msg = "LOCALGENERATE: No scene_id provided"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"LOCALGENERATE: Processing scene ID: {scene_id}")
    stash_service = None

    try:
        # Initial progress
        await progress_callback(
            0, f"LOCALGENERATE: Starting generation for scene {scene_id}"
        )

        # Load settings and initialize Stash service
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url, api_key=settings.stash.api_key
        )

        await progress_callback(
            10, f"LOCALGENERATE: Querying scene {scene_id} from Stash"
        )

        # Fetch scene data
        scene = await _fetch_scene_data(stash_service, scene_id)
        scene_title = scene.get("title", f"Scene {scene_id}")
        logger.info(f"LOCALGENERATE: Found scene: {scene_title}")

        # Validate and get video file path and oshash
        video_path, scene_hash = await _validate_and_extract_file_info(scene, scene_id)
        logger.info(f"LOCALGENERATE: Video file: {video_path}")
        logger.info(f"LOCALGENERATE: Using oshash: {scene_hash}")

        # Get video dimensions
        width = scene.get("files", [{}])[0].get("width", 1920)

        # Get scene markers
        scene_markers = scene.get("scene_markers", [])
        if not scene_markers:
            logger.info(f"LOCALGENERATE: No scene markers found for scene {scene_id}")
            await progress_callback(
                100, f"LOCALGENERATE: No markers to process for scene {scene_id}"
            )
            return {
                "job_id": job_id,
                "status": "completed",
                "total_markers": 0,
                "generated_screenshots": 0,
                "generated_previews": 0,
                "scene_id": scene_id,
            }

        logger.info(f"LOCALGENERATE: Found {len(scene_markers)} markers")

        # Process all markers
        try:
            stats = await _process_all_markers(
                scene_markers,
                video_path,
                scene_hash,
                width,
                job_id,
                cancellation_token,
                progress_callback,
            )
        except asyncio.CancelledError:
            return {"status": "cancelled", "job_id": job_id}

        # Final progress
        await progress_callback(
            100, f"LOCALGENERATE: Generation completed for scene {scene_id}"
        )

        # Summary logging
        logger.info(
            f"LOCALGENERATE: Job completed - Generated {stats['generated_screenshots']} screenshots, "
            f"{stats['generated_previews']} previews"
        )
        logger.info(
            f"LOCALGENERATE: Skipped {stats['skipped_screenshots']} existing screenshots, "
            f"{stats['skipped_previews']} existing previews"
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "scene_id": scene_id,
            "scene_title": scene_title,
            **stats,
        }

    except ValueError as e:
        logger.error(str(e))
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }
    except Exception as e:
        error_msg = f"LOCALGENERATE: Job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise
    finally:
        if stash_service:
            await stash_service.close()


def register_local_generate_jobs(job_service: JobService) -> None:
    """Register job handlers with the job service."""
    job_service.register_handler(JobType.LOCAL_GENERATE, local_generate_job)
    logger.info("Registered local generate job handlers")
