"""Service for checking and managing pending downloads.

This service provides a single source of truth for checking download status,
particularly for torrents that need to be processed from qBittorrent.
"""

import logging
from typing import Any, List, Optional

import qbittorrentapi

from app.core.settings_loader import load_settings_with_db_overrides

logger = logging.getLogger(__name__)


class DownloadCheckService:
    """Service for checking and managing pending downloads from qBittorrent."""

    async def connect_to_qbittorrent(self) -> qbittorrentapi.Client:
        """Connect and authenticate to qBittorrent.

        This is the centralized method for connecting to qBittorrent.

        Returns:
            Authenticated qBittorrent client

        Raises:
            Exception: If connection or authentication fails
        """
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

    def _filter_pending_torrents(self, torrents: List[Any]) -> List[Any]:
        """Filter torrents to only include those pending processing.

        Args:
            torrents: List of torrent objects from qBittorrent

        Returns:
            List of torrents that don't have 'synced' or 'error_syncing' tags
        """
        filtered_torrents = []
        for torrent in torrents:
            logger.debug(
                f"Torrent '{torrent.name}' has tags: {torrent.tags} (type: {type(torrent.tags)})"
            )

            # Handle different possible types for tags
            if isinstance(torrent.tags, str):
                # If tags is a comma-separated string
                tags_list = [
                    tag.strip() for tag in torrent.tags.split(",") if tag.strip()
                ]
                has_synced = "synced" in tags_list
                has_error = "error_syncing" in tags_list
            elif isinstance(torrent.tags, list):
                # If tags is already a list
                has_synced = "synced" in torrent.tags
                has_error = "error_syncing" in torrent.tags
            else:
                # If tags is None or some other type
                logger.warning(
                    f"Unexpected tags type for torrent '{torrent.name}': {type(torrent.tags)}"
                )
                has_synced = False
                has_error = False

            if not has_synced and not has_error:
                filtered_torrents.append(torrent)
                logger.debug(
                    f"Including torrent '{torrent.name}' (no 'synced' or 'error_syncing' tag)"
                )
            else:
                skip_reason = "synced" if has_synced else "error_syncing"
                logger.debug(
                    f"Skipping torrent '{torrent.name}' (has '{skip_reason}' tag)"
                )

        return filtered_torrents

    async def get_pending_downloads(self) -> List[Any]:
        """Get list of pending downloads (torrents) that need processing.

        This is the single source of truth for getting torrents that need processing.

        Returns:
            List of torrent objects pending processing
        """
        qbt_client: Optional[qbittorrentapi.Client] = None
        try:
            # Connect to qBittorrent
            qbt_client = await self.connect_to_qbittorrent()

            # Get all completed torrents in xxx category
            logger.info("Fetching completed torrents with category 'xxx'")
            torrents = qbt_client.torrents_info(
                status_filter="completed", category="xxx"
            )
            logger.info(f"Found {len(torrents)} completed torrents in category 'xxx'")

            # Filter to pending torrents
            filtered_torrents = self._filter_pending_torrents(list(torrents))
            logger.info(
                f"Filtered to {len(filtered_torrents)} torrents without 'synced' or 'error_syncing' tags"
            )

            return filtered_torrents

        except Exception as e:
            logger.error(f"Error getting pending downloads: {str(e)}", exc_info=True)
            return []
        finally:
            # Clean up connection
            if qbt_client is not None:
                try:
                    qbt_client.auth_log_out()
                except Exception:
                    pass  # Ignore logout errors

    async def get_pending_downloads_count(self) -> int:
        """Get the count of pending downloads.

        Returns:
            Count of pending downloads (0 if unable to check)
        """
        try:
            pending_downloads = await self.get_pending_downloads()
            return len(pending_downloads)
        except Exception as e:
            logger.error(
                f"Error checking pending downloads count: {str(e)}", exc_info=True
            )
            return 0


# Singleton instance
download_check_service = DownloadCheckService()
