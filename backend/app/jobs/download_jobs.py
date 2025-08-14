import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import qbittorrentapi

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models.handled_download import HandledDownload
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


def _initialize_result(job_id: str, total_items: int) -> Dict[str, Any]:
    """Initialize result tracking dictionary."""
    return {
        "job_id": job_id,
        "status": "completed",
        "total_items": total_items,
        "processed_items": 0,
        "synced_items": 0,
        "skipped_items": 0,
        "failed_items": 0,
        "total_files_linked": 0,
        "total_files_under_duration": 0,
        "total_files_skipped": 0,
        "errors": [],
    }


async def _record_handled_download(
    download_name: str, destination_path: str, job_id: str
) -> None:
    """Record a handled download in the database.

    Creates its own database session to avoid greenlet errors.
    """
    try:
        async with AsyncSessionLocal() as db:
            handled_download = HandledDownload(
                download_name=download_name,
                destination_path=destination_path,
                job_id=job_id,
            )
            db.add(handled_download)
            await db.commit()
            logger.debug(
                f"Recorded handled download: {download_name} -> {destination_path}"
            )
    except Exception as e:
        logger.error(f"Failed to record handled download: {str(e)}", exc_info=True)
        # Don't fail the whole job just because we couldn't log the download


def _add_synced_tag(torrent: Any) -> None:
    """Add 'synced' tag to torrent."""
    try:
        logger.debug(f"Adding 'synced' tag to torrent: {torrent.name}")
        torrent.add_tags("synced")
        logger.info(f"Successfully synced torrent: {torrent.name}")
    except Exception as e:
        logger.error(
            f"Failed to add 'synced' tag to torrent '{torrent.name}': {str(e)}"
        )
        # Don't fail the whole process just because we couldn't add a tag
        logger.warning("Continuing despite tag addition failure")


def _add_error_syncing_tag(torrent: Any) -> None:
    """Add 'error_syncing' tag to torrent that failed processing."""
    try:
        logger.debug(f"Adding 'error_syncing' tag to torrent: {torrent.name}")
        torrent.add_tags("error_syncing")
        logger.info(f"Marked torrent as error_syncing: {torrent.name}")
    except Exception as e:
        logger.error(
            f"Failed to add 'error_syncing' tag to torrent '{torrent.name}': {str(e)}"
        )
        # Don't fail the whole process just because we couldn't add a tag
        logger.warning("Continuing despite tag addition failure")


def _copy_torrent_content(content_path: Path, dest_path: Path) -> List[Path]:
    """Copy torrent content when hardlinking fails.

    Returns:
        List of paths that were successfully copied.
    """
    copied_files: List[Path] = []

    if content_path.is_file():
        if not dest_path.exists():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(content_path, dest_path)
            copied_files.append(dest_path)
            logger.info(f"Successfully copied {content_path} to {dest_path} (fallback)")
        else:
            logger.info(f"Destination already exists during copy fallback: {dest_path}")
    else:
        # For directory copy, track all copied files
        for src_file in content_path.rglob("*"):
            if src_file.is_file():
                rel_path = src_file.relative_to(content_path)
                dst_file = dest_path / rel_path
                if not dst_file.exists():
                    copied_files.append(dst_file)
        shutil.copytree(content_path, dest_path, dirs_exist_ok=True)
        logger.info(f"Successfully copied {content_path} to {dest_path} (fallback)")

    return copied_files


def _get_video_duration(file_path: Path) -> Optional[float]:
    """Get video duration in seconds using ffprobe.

    Returns:
        Duration in seconds, or None if unable to determine.
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
        logger.warning(f"Failed to get duration for {file_path}: {e}")
    return None


def _is_video_file(file_path: Path) -> bool:
    """Check if file is a video based on extension."""
    video_extensions = {
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".3gp",
        ".mp2",
        ".mpe",
        ".mpv",
        ".m2v",
        ".svi",
        ".3g2",
        ".mxf",
        ".roq",
        ".nsv",
        ".f4v",
        ".f4p",
        ".f4a",
        ".f4b",
    }
    return file_path.suffix.lower() in video_extensions


def _analyze_file_for_duration(
    src_file: Path,
    dst_file: Path,
    exclude_small_vids: bool,
) -> Tuple[bool, bool, bool]:
    """Analyze a file for video duration.

    Returns:
        Tuple of (should_process, is_under_duration, was_skipped_for_duration)
    """
    if not _is_video_file(src_file):
        return True, False, False

    duration = _get_video_duration(src_file)
    if duration is not None and duration < 30:
        if exclude_small_vids:
            logger.info(
                f"Skipping video file {src_file.name} (duration: {duration:.1f}s < 30s)"
            )
            return False, True, True
        return True, True, False

    return True, False, False


def _collect_files_to_process(
    content_path: Path,
    dest_path: Path,
    exclude_small_vids: bool,
) -> Tuple[List[Tuple[Path, Path]], int, int]:
    """Collect files to process and analyze video durations.

    Returns:
        Tuple of (files_to_process, files_under_duration_count, skipped_due_to_duration_count)
    """
    files_to_process: List[Tuple[Path, Path]] = []
    files_under_duration = 0
    skipped_due_to_duration = 0

    if content_path.is_file():
        # Single file torrent
        should_process, is_under, was_skipped = _analyze_file_for_duration(
            content_path, dest_path, exclude_small_vids
        )
        if is_under:
            files_under_duration += 1
        if was_skipped:
            skipped_due_to_duration += 1
        elif should_process:
            files_to_process.append((content_path, dest_path))
    else:
        # Directory torrent - check each file
        for src_file in content_path.rglob("*"):
            if src_file.is_file():
                rel_path = src_file.relative_to(content_path)
                dst_file = dest_path / rel_path

                should_process, is_under, was_skipped = _analyze_file_for_duration(
                    src_file, dst_file, exclude_small_vids
                )
                if is_under:
                    files_under_duration += 1
                if was_skipped:
                    skipped_due_to_duration += 1
                elif should_process:
                    files_to_process.append((src_file, dst_file))

    return files_to_process, files_under_duration, skipped_due_to_duration


def _link_or_copy_file(src_file: Path, dst_file: Path) -> bool:
    """Link or copy a single file.

    Returns:
        True if file was linked/copied, False if it already exists.
    """
    if dst_file.exists():
        logger.debug(f"Destination file already exists: {dst_file}")
        return False

    dst_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Try hardlink first
        os.link(src_file, dst_file)
        return True
    except OSError as e:
        if e.errno == 18:  # Cross-device link error
            logger.debug(f"Cross-filesystem hardlink failed for {src_file}, using copy")
            shutil.copy2(src_file, dst_file)
            return True
        else:
            raise


def _hardlink_torrent_content(content_path: Path, dest_path: Path) -> List[Path]:
    """Hardlink torrent content to destination.

    Returns:
        List of paths that were successfully linked.
    """
    linked_files: List[Path] = []

    if content_path.is_file():
        # Single file torrent
        if dest_path.exists():
            logger.debug(f"Destination file already exists: {dest_path}")
            return linked_files
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        os.link(content_path, dest_path)
        linked_files.append(dest_path)
    else:
        # Directory torrent - hardlink each file individually
        for src_file in content_path.rglob("*"):
            if src_file.is_file():
                rel_path = src_file.relative_to(content_path)
                dst_file = dest_path / rel_path

                if dst_file.exists():
                    logger.debug(f"Destination file already exists: {dst_file}")
                    continue

                dst_file.parent.mkdir(parents=True, exist_ok=True)
                os.link(src_file, dst_file)
                linked_files.append(dst_file)

    return linked_files


async def _process_single_torrent(
    torrent: Any,
    dest_base: Path,
    result: Dict[str, Any],
    job_id: str,
    exclude_small_vids: bool = False,
) -> None:
    """Process a single torrent.

    Args:
        torrent: The torrent to process
        dest_base: Base destination directory
        result: Result tracking dictionary
        job_id: Job ID for tracking
        exclude_small_vids: If True, skip video files under 30 seconds
    """
    logger.info(f"Processing torrent: {torrent.name}")
    logger.debug(
        f"Torrent details - Hash: {torrent.hash}, Content path: {torrent.content_path}"
    )

    # Get the torrent's content path
    content_path = Path(torrent.content_path)

    if not content_path.exists():
        logger.error(f"Content path does not exist: {content_path}")
        result["failed_items"] += 1
        result["errors"].append(
            {
                "torrent": torrent.name,
                "error": f"Content path does not exist: {content_path}",
            }
        )
        # Add error_syncing tag when content path doesn't exist
        _add_error_syncing_tag(torrent)
        return

    # Determine destination path
    dest_path = dest_base / torrent.name

    # Collect files to process with duration checking
    files_to_process, files_under_duration, skipped_due_to_duration = (
        _collect_files_to_process(content_path, dest_path, exclude_small_vids)
    )

    # Update counters
    result["total_files_under_duration"] += files_under_duration
    result["total_files_skipped"] += skipped_due_to_duration

    # Process files
    linked_files, files_already_exist = await _process_files(
        files_to_process, content_path, dest_path
    )

    # Update result counters
    result["total_files_linked"] += len(linked_files)
    result["total_files_skipped"] += files_already_exist

    if linked_files:
        logger.debug(
            f"Successfully processed {len(linked_files)} files from {content_path} to {dest_path}"
        )
    else:
        logger.info(
            f"No new files to process for {torrent.name} (skipped: {files_already_exist + skipped_due_to_duration})"
        )

    # Record each linked/copied file in the database
    for file_path in linked_files:
        await _record_handled_download(
            download_name=torrent.name, destination_path=str(file_path), job_id=job_id
        )

    # Add "synced" tag to torrent
    _add_synced_tag(torrent)

    result["synced_items"] += 1
    result["processed_items"] += 1


async def _process_files(
    files_to_process: List[Tuple[Path, Path]],
    content_path: Path,
    dest_path: Path,
) -> Tuple[List[Path], int]:
    """Process (link or copy) files to destination.

    Returns:
        Tuple of (linked_files, files_already_exist_count)
    """
    logger.info(
        f"Processing {len(files_to_process)} files from {content_path} to {dest_path}"
    )
    linked_files: List[Path] = []
    files_already_exist = 0

    for src_file, dst_file in files_to_process:
        if _link_or_copy_file(src_file, dst_file):
            linked_files.append(dst_file)
        else:
            files_already_exist += 1

    return linked_files, files_already_exist


async def _get_completed_torrents(qbt_client: Any) -> List[Any]:
    """Get all completed torrents with category 'xxx' that don't have 'synced' or 'error_syncing' tags."""
    try:
        # Get all completed torrents in xxx category
        logger.info("Fetching completed torrents with category 'xxx'")
        # Note: status_filter should be a string, not a list
        torrents = qbt_client.torrents_info(status_filter="completed", category="xxx")
        logger.info(f"Found {len(torrents)} completed torrents in category 'xxx'")

        # Filter out torrents that already have the "synced" or "error_syncing" tags
        filtered_torrents = []
        for t in torrents:
            logger.debug(
                f"Torrent '{t.name}' has tags: {t.tags} (type: {type(t.tags)})"
            )

            # Handle different possible types for tags
            if isinstance(t.tags, str):
                # If tags is a comma-separated string
                tags_list = [tag.strip() for tag in t.tags.split(",") if tag.strip()]
                has_synced = "synced" in tags_list
                has_error = "error_syncing" in tags_list
            elif isinstance(t.tags, list):
                # If tags is already a list
                has_synced = "synced" in t.tags
                has_error = "error_syncing" in t.tags
            else:
                # If tags is None or some other type
                logger.warning(
                    f"Unexpected tags type for torrent '{t.name}': {type(t.tags)}"
                )
                has_synced = False
                has_error = False

            if not has_synced and not has_error:
                filtered_torrents.append(t)
                logger.debug(
                    f"Including torrent '{t.name}' (no 'synced' or 'error_syncing' tag)"
                )
            else:
                skip_reason = "synced" if has_synced else "error_syncing"
                logger.debug(f"Skipping torrent '{t.name}' (has '{skip_reason}' tag)")

        logger.info(
            f"Filtered to {len(filtered_torrents)} torrents without 'synced' or 'error_syncing' tags"
        )
        return filtered_torrents

    except Exception as e:
        logger.error(f"Error getting completed torrents: {str(e)}", exc_info=True)
        raise


async def _connect_to_qbittorrent() -> Any:
    """Connect and authenticate to qBittorrent."""
    settings = await load_settings_with_db_overrides()

    logger.info(
        f"Attempting to connect to qBittorrent at {settings.qbittorrent.host}:{settings.qbittorrent.port}"
    )

    qbt_client = qbittorrentapi.Client(
        host=settings.qbittorrent.host,
        port=settings.qbittorrent.port,
        username=settings.qbittorrent.username,
        password=settings.qbittorrent.password,
    )

    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        logger.error(f"Failed to authenticate with qBittorrent: {str(e)}")
        raise Exception(
            f"Failed to authenticate with qBittorrent. Invalid credentials: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Failed to connect to qBittorrent at {settings.qbittorrent.host}:{settings.qbittorrent.port}. Error: {str(e)}"
        )
        raise Exception(
            f"Failed to connect to qBittorrent. Connection Error: {type(e).__name__}({str(e)})"
        )

    logger.info("Successfully connected to qBittorrent")
    return qbt_client


async def _process_torrents(
    completed_torrents: List[Any],
    dest_base: Path,
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    exclude_small_vids: bool = False,
) -> None:
    """Process all completed torrents.

    Args:
        completed_torrents: List of torrents to process
        dest_base: Base destination directory
        result: Result tracking dictionary
        progress_callback: Progress callback function
        cancellation_token: Cancellation token
        exclude_small_vids: If True, skip video files under 30 seconds
    """
    for idx, torrent in enumerate(completed_torrents):
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Job {result['job_id']} cancelled")
            result["status"] = "cancelled"
            break

        # Update progress
        progress = int((idx / len(completed_torrents)) * 100)
        await progress_callback(
            progress,
            f"Processing torrent {idx + 1}/{len(completed_torrents)}: {torrent.name}",
        )

        try:
            await _process_single_torrent(
                torrent, dest_base, result, result["job_id"], exclude_small_vids
            )
        except Exception as e:
            logger.error(f"Error processing torrent '{torrent.name}': {str(e)}")
            result["failed_items"] += 1
            result["errors"].append({"torrent": torrent.name, "error": str(e)})
            # Add error_syncing tag to failed torrent
            _add_error_syncing_tag(torrent)


async def process_downloads_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Process completed torrents from qBittorrent.

    Args:
        job_id: Job ID
        progress_callback: Progress callback function
        cancellation_token: Cancellation token
        **kwargs: Additional parameters including:
            - exclude_small_vids: If True, skip video files under 30 seconds (default: False)
    """
    logger.info(f"Starting process_downloads job {job_id}")
    qbt_client = None

    # Get exclude_small_vids flag from kwargs (default to False)
    exclude_small_vids = kwargs.get("exclude_small_vids", False)
    logger.info(f"Exclude small videos flag: {exclude_small_vids}")

    try:
        # Initial progress
        await progress_callback(0, "Starting download processing job")

        # Connect to qBittorrent
        logger.debug("Connecting to qBittorrent...")
        await progress_callback(5, "Connecting to qBittorrent...")
        qbt_client = await _connect_to_qbittorrent()

        # Get completed torrents without 'synced' tag
        logger.debug("Getting completed torrents...")
        await progress_callback(10, "Fetching completed torrents...")
        completed_torrents = await _get_completed_torrents(qbt_client)
        logger.info(
            f"Found {len(completed_torrents)} completed torrents with category 'xxx' to process"
        )

        if not completed_torrents:
            return _initialize_result(job_id, 0)

        # Initialize result and destination
        result = _initialize_result(job_id, len(completed_torrents))
        dest_base = Path("/downloads/avideos/")
        dest_base.mkdir(parents=True, exist_ok=True)

        # Process all torrents
        await _process_torrents(
            completed_torrents,
            dest_base,
            result,
            progress_callback,
            cancellation_token,
            exclude_small_vids,
        )

        # Final updates
        await progress_callback(100, "Download processing complete")
        if result["failed_items"] > 0:
            result["status"] = "completed_with_errors"

        logger.info(
            f"Download processing completed: "
            f"{result['synced_items']} synced, "
            f"{result['total_files_linked']} files linked, "
            f"{result['total_files_under_duration']} files under 30s, "
            f"{result['total_files_skipped']} files skipped, "
            f"{result['failed_items']} failed"
        )

        return result

    except Exception as e:
        error_msg = f"Download processing job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await progress_callback(100, error_msg)
        raise
    finally:
        # Clean up qBittorrent client connection
        if qbt_client is not None:
            qbt_client.auth_log_out()


def register_download_jobs(job_service: JobService) -> None:
    """Register download job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.PROCESS_DOWNLOADS, process_downloads_job)

    logger.info("Registered download job handlers")
