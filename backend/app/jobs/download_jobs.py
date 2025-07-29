import logging
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import qbittorrentapi

from app.core.settings_loader import load_settings_with_db_overrides
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


def _copy_torrent_content(content_path: Path, dest_path: Path) -> None:
    """Copy torrent content to destination."""
    if content_path.is_file():
        # Single file torrent
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(content_path, dest_path)
    else:
        # Directory torrent
        shutil.copytree(content_path, dest_path, dirs_exist_ok=True)


def _process_single_torrent(
    torrent: Any, dest_base: Path, result: Dict[str, Any]
) -> None:
    """Process a single torrent."""
    logger.info(f"Processing torrent: {torrent.name}")

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

    # Copy files/directories recursively
    logger.info(f"Copying from {content_path} to {dest_path}")
    _copy_torrent_content(content_path, dest_path)

    # Add "synced" tag to torrent
    torrent.add_tags("synced")
    logger.info(f"Successfully synced torrent: {torrent.name}")

    result["synced_items"] += 1
    result["processed_items"] += 1


async def _get_completed_torrents(qbt_client: Any) -> List[Any]:
    """Get all completed torrents with category 'xxx' that don't have 'synced' tag."""
    # Get all completed torrents in xxx category
    torrents = qbt_client.torrents_info(status_filter=["completed"], category="xxx")
    # Filter out torrents that already have the "synced" tag
    return [t for t in torrents if "synced" not in t.tags]


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


def _process_torrents(
    completed_torrents: List[Any],
    dest_base: Path,
    result: Dict[str, Any],
    progress_callback: Callable[[int, Optional[str]], None],
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
        progress_callback(progress, f"Processing torrent: {torrent.name}")

        try:
            _process_single_torrent(torrent, dest_base, result)
        except Exception as e:
            logger.error(f"Error processing torrent '{torrent.name}': {str(e)}")
            result["failed_items"] += 1
            result["errors"].append({"torrent": torrent.name, "error": str(e)})


async def process_downloads_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Process completed torrents from qBittorrent."""
    logger.info(f"Starting process_downloads job {job_id}")
    qbt_client = None

    try:
        # Connect to qBittorrent
        qbt_client = await _connect_to_qbittorrent()

        # Get completed torrents without 'synced' tag
        completed_torrents = await _get_completed_torrents(qbt_client)
        logger.info(
            f"Found {len(completed_torrents)} completed torrents with category 'xxx' to process"
        )

        if not completed_torrents:
            return _initialize_result(job_id, 0)

        # Initialize result and destination
        result = _initialize_result(job_id, len(completed_torrents))
        dest_base = Path("/opt/media/downloads/avideos/")
        dest_base.mkdir(parents=True, exist_ok=True)

        # Process all torrents
        _process_torrents(
            completed_torrents, dest_base, result, progress_callback, cancellation_token
        )

        # Final updates
        progress_callback(100, "Download processing complete")
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
        logger.error(f"Download processing job failed: {str(e)}")
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
