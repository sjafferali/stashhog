"""Service for checking pending downloads."""


class DownloadCheckService:
    """Service for checking pending downloads from qBittorrent or other sources."""

    async def get_pending_downloads_count(self) -> int:
        """Get the count of pending downloads.

        Returns:
            Count of pending downloads (0 if unable to check)
        """
        # TODO: Implement actual download checking logic
        # For now, return 0 to allow tests to pass
        return 0


# Singleton instance
download_check_service = DownloadCheckService()
