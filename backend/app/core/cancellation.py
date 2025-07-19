"""
Cancellation token implementation for background jobs.

This module provides a simple cancellation token mechanism that allows
background jobs to check if they should stop processing.
"""

import asyncio
from typing import Dict, Optional


class CancellationToken:
    """Token that can be used to check if a job should be cancelled."""

    def __init__(self) -> None:
        self._cancelled = False
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Mark this token as cancelled."""
        self._cancelled = True
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if the token has been cancelled."""
        return self._cancelled

    async def check_cancellation(self) -> None:
        """Check if cancelled and raise CancelledError if so."""
        if self._cancelled:
            raise asyncio.CancelledError("Job was cancelled")

    async def wait_for_cancellation(self) -> None:
        """Wait until the token is cancelled."""
        await self._event.wait()


class CancellationTokenManager:
    """Manages cancellation tokens for jobs."""

    def __init__(self) -> None:
        self._tokens: Dict[str, CancellationToken] = {}

    def create_token(self, job_id: str) -> CancellationToken:
        """Create a new cancellation token for a job."""
        token = CancellationToken()
        self._tokens[job_id] = token
        return token

    def get_token(self, job_id: str) -> Optional[CancellationToken]:
        """Get the cancellation token for a job."""
        return self._tokens.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job by its ID."""
        token = self._tokens.get(job_id)
        if token:
            token.cancel()
            return True
        return False

    def remove_token(self, job_id: str) -> None:
        """Remove a token after job completion."""
        self._tokens.pop(job_id, None)


# Global instance
cancellation_manager = CancellationTokenManager()
