"""Service for checking pending downloads."""

import logging

import qbittorrentapi

from app.core.settings_loader import load_settings_with_db_overrides

logger = logging.getLogger(__name__)


class DownloadCheckService:
    """Service for checking pending downloads from qBittorrent or other sources."""

    async def get_pending_downloads_count(self) -> int:
        """Get the count of pending downloads.

        Returns:
            Count of pending downloads (0 if unable to check)
        """
        try:
            # Get qBittorrent settings
            settings = await load_settings_with_db_overrides()
            qbt_settings = settings.qbittorrent

            # Build the host URL
            qbt_host = f"http://{qbt_settings.host}:{qbt_settings.port}"

            # Connect to qBittorrent
            qbt_client = qbittorrentapi.Client(
                host=qbt_host,
                username=qbt_settings.username,
                password=qbt_settings.password,
            )

            # Authenticate
            try:
                qbt_client.auth_log_in()
            except qbittorrentapi.LoginFailed as e:
                logger.error(f"Failed to authenticate with qBittorrent: {str(e)}")
                return 0

            # Get completed torrents with category 'xxx' that don't have 'synced' or 'error_syncing' tags
            torrents = qbt_client.torrents_info(
                status_filter="completed", category="xxx"
            )

            # Filter out torrents that already have the "synced" or "error_syncing" tags
            pending_count = 0
            for torrent in torrents:
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
                    # If tags is None or some other type, assume no tags
                    has_synced = False
                    has_error = False

                if not has_synced and not has_error:
                    pending_count += 1

            return pending_count

        except Exception as e:
            logger.error(f"Error checking pending downloads: {str(e)}", exc_info=True)
            return 0


# Singleton instance
download_check_service = DownloadCheckService()
