import logging
import os
import shutil
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

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
    torrent: Any, dest_base: Path, result: Dict[str, Any], job_id: str
) -> None:
    """Process a single torrent."""
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
        return

    # Determine destination path
    dest_path = dest_base / torrent.name

    # Hardlink files/directories
    logger.info(f"Hardlinking from {content_path} to {dest_path}")
    linked_files: List[Path] = []
    try:
        linked_files = _hardlink_torrent_content(content_path, dest_path)
        if linked_files:
            logger.debug(
                f"Successfully hardlinked {len(linked_files)} files from {content_path} to {dest_path}"
            )
        else:
            logger.info(
                f"All files already exist for {torrent.name}, skipping hardlink"
            )
    except OSError as e:
        if e.errno == 18:  # Cross-device link error
            logger.warning(
                f"Cross-filesystem hardlink failed, falling back to copy: {e}"
            )
            linked_files = _copy_torrent_content(content_path, dest_path)
        else:
            raise

    # Record each linked/copied file in the database
    for file_path in linked_files:
        await _record_handled_download(
            download_name=file_path.name, destination_path=str(file_path), job_id=job_id
        )

    # Add "synced" tag to torrent
    _add_synced_tag(torrent)

    result["synced_items"] += 1
    result["processed_items"] += 1


async def _get_completed_torrents(qbt_client: Any) -> List[Any]:
    """Get all completed torrents with category 'xxx' that don't have 'synced' tag."""
    try:
        # Get all completed torrents in xxx category
        logger.info("Fetching completed torrents with category 'xxx'")
        # Note: status_filter should be a string, not a list
        torrents = qbt_client.torrents_info(status_filter="completed", category="xxx")
        logger.info(f"Found {len(torrents)} completed torrents in category 'xxx'")

        # Filter out torrents that already have the "synced" tag
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
            elif isinstance(t.tags, list):
                # If tags is already a list
                has_synced = "synced" in t.tags
            else:
                # If tags is None or some other type
                logger.warning(
                    f"Unexpected tags type for torrent '{t.name}': {type(t.tags)}"
                )
                has_synced = False

            if not has_synced:
                filtered_torrents.append(t)
                logger.debug(f"Including torrent '{t.name}' (no 'synced' tag)")
            else:
                logger.debug(f"Skipping torrent '{t.name}' (has 'synced' tag)")

        logger.info(
            f"Filtered to {len(filtered_torrents)} torrents without 'synced' tag"
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
) -> None:
    """Process all completed torrents."""
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
            await _process_single_torrent(torrent, dest_base, result, result["job_id"])
        except Exception as e:
            logger.error(f"Error processing torrent '{torrent.name}': {str(e)}")
            result["failed_items"] += 1
            result["errors"].append({"torrent": torrent.name, "error": str(e)})


async def process_downloads_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Process completed torrents from qBittorrent."""
    logger.info(f"Starting process_downloads job {job_id}")
    qbt_client = None

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
            completed_torrents, dest_base, result, progress_callback, cancellation_token
        )

        # Final updates
        await progress_callback(100, "Download processing complete")
        if result["failed_items"] > 0:
            result["status"] = "completed_with_errors"

        logger.info(
            f"Download processing completed: "
            f"{result['synced_items']} synced, "
            f"{result['skipped_items']} skipped, "
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
