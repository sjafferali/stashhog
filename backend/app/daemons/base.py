import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.database import AsyncSessionLocal
from app.models.daemon import (
    Daemon,
    DaemonJobAction,
    DaemonJobHistory,
    DaemonLog,
    DaemonStatus,
    LogLevel,
)


class BaseDaemon(ABC):
    """
    Base class for all daemons.

    Provides common functionality for:
    - Lifecycle management (start/stop)
    - Logging
    - Heartbeat updates
    - Job tracking
    - Configuration handling
    """

    # Must be overridden by subclasses
    daemon_type: Optional[str] = None

    def __init__(self, daemon_id: str, config: Optional[Dict[str, Any]] = None):
        self.daemon_id = daemon_id
        self.config = config or {}
        self.is_running = False
        self.status = DaemonStatus.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None

    async def start(self):
        """Start the daemon."""
        if self.is_running:
            return

        self.is_running = True
        self.status = DaemonStatus.RUNNING
        self._start_time = datetime.utcnow()

        # Update daemon status in database
        async with AsyncSessionLocal() as db:
            daemon = await db.get(Daemon, self.daemon_id)
            if daemon:
                daemon.status = DaemonStatus.RUNNING.value
                daemon.started_at = self._start_time
                await db.commit()

        # Call lifecycle hook
        await self.on_start()

        # Start the main run loop
        self._task = asyncio.create_task(self._run_wrapper())

    async def stop(self):
        """Stop the daemon gracefully."""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel the task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Call lifecycle hook
        await self.on_stop()

        # Update daemon status in database
        async with AsyncSessionLocal() as db:
            daemon = await db.get(Daemon, self.daemon_id)
            if daemon:
                daemon.status = DaemonStatus.STOPPED.value
                daemon.started_at = None
                await db.commit()

        self.status = DaemonStatus.STOPPED

    async def _run_wrapper(self):
        """Wrapper for the run method that handles errors."""
        try:
            await self.run()
        except asyncio.CancelledError:
            # Normal shutdown
            raise
        except Exception as e:
            # Unexpected error
            await self.log(LogLevel.ERROR, f"Daemon crashed: {str(e)}")
            self.status = DaemonStatus.ERROR

            # Update status in database
            async with AsyncSessionLocal() as db:
                daemon = await db.get(Daemon, self.daemon_id)
                if daemon:
                    daemon.status = DaemonStatus.ERROR.value
                    await db.commit()

            raise

    @abstractmethod
    async def run(self):
        """
        Main daemon execution loop.

        This method should:
        - Run continuously while self.is_running is True
        - Handle asyncio.CancelledError for graceful shutdown
        - Log errors but continue running
        - Update heartbeat periodically
        """
        pass

    async def on_start(self):
        """Called when daemon starts. Override to initialize resources."""
        pass

    async def on_stop(self):
        """Called when daemon stops. Override to clean up resources."""
        pass

    async def log(self, level: LogLevel, message: str):
        """Log a message to the database and broadcast via WebSocket."""
        import logging

        logger = logging.getLogger(__name__)

        async with AsyncSessionLocal() as db:
            log_entry = DaemonLog(
                daemon_id=self.daemon_id, level=level.value, message=message
            )
            db.add(log_entry)
            await db.commit()

            # Broadcast via WebSocket (will be implemented in WebSocket manager)
            logger.info(
                f"About to broadcast daemon log for daemon_id: {self.daemon_id}"
            )
            try:
                from app.services.websocket_manager import websocket_manager

                logger.info(
                    f"Successfully imported websocket_manager: {websocket_manager}"
                )

                await websocket_manager.broadcast_daemon_log(
                    daemon_id=str(self.daemon_id), log=log_entry.to_dict()
                )
                logger.info("Finished broadcasting daemon log")
            except Exception as e:
                logger.error(f"Failed to broadcast daemon log: {e}", exc_info=True)

    async def update_heartbeat(self):
        """Update the daemon's heartbeat timestamp."""
        async with AsyncSessionLocal() as db:
            daemon = await db.get(Daemon, self.daemon_id)
            if daemon:
                daemon.last_heartbeat = datetime.utcnow()
                await db.commit()

    async def track_job_action(
        self, job_id: str, action: DaemonJobAction, reason: Optional[str] = None
    ):
        """Track an action performed on a job."""
        async with AsyncSessionLocal() as db:
            history = DaemonJobHistory(
                daemon_id=self.daemon_id,
                job_id=job_id,
                action=action.value,
                reason=reason,
            )
            db.add(history)
            await db.commit()

            # Broadcast update
            from app.services.websocket_manager import websocket_manager

            await websocket_manager.broadcast_daemon_job_action(
                daemon_id=str(self.daemon_id), action=history.to_dict()
            )

    def get_uptime_seconds(self) -> float:
        """Get daemon uptime in seconds."""
        if not self._start_time or not self.is_running:
            return 0
        return (datetime.utcnow() - self._start_time).total_seconds()
