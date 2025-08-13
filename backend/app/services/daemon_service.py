import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.daemons import get_daemon_classes
from app.daemons.base import BaseDaemon
from app.models.daemon import (
    Daemon,
    DaemonJobHistory,
    DaemonLog,
    DaemonType,
    LogLevel,
)

logger = logging.getLogger(__name__)


class DaemonService:
    """
    Service for managing daemon lifecycle and operations.

    Responsibilities:
    - Starting/stopping daemons
    - Managing daemon instances
    - Auto-starting daemons on service initialization
    - Health monitoring
    - Log and history queries
    """

    def __init__(self) -> None:
        self._daemons: Dict[str, BaseDaemon] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the daemon service and auto-start enabled daemons."""
        if self._initialized:
            return

        logger.info("Initializing daemon service")

        # Skip auto-start in test environment
        import os

        if os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("Skipping daemon auto-start in test environment")
            self._initialized = True
            return

        # Load and auto-start enabled daemons
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Daemon).where(Daemon.auto_start.is_(True))
                )
                auto_start_daemons = result.scalars().all()

                for daemon_record in auto_start_daemons:
                    try:
                        await self.start_daemon(str(daemon_record.id))
                        logger.info(f"Auto-started daemon: {daemon_record.name}")
                    except Exception as e:
                        logger.error(
                            f"Failed to auto-start daemon {daemon_record.name}: {e}"
                        )
        except Exception as e:
            # Handle case where table doesn't exist (e.g., before migrations)
            logger.warning(f"Could not load daemons for auto-start: {e}")

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown all running daemons."""
        logger.info("Shutting down daemon service")

        # Stop all running daemons
        daemon_ids = list(self._daemons.keys())
        for daemon_id in daemon_ids:
            try:
                await self.stop_daemon(daemon_id)
            except Exception as e:
                logger.error(f"Error stopping daemon {daemon_id}: {e}")

        self._initialized = False

    async def get_all_daemons(self, db: AsyncSession) -> List[Daemon]:
        """Get all daemon records."""
        result = await db.execute(select(Daemon).order_by(Daemon.name))
        return list(result.scalars().all())

    async def get_daemon(self, db: AsyncSession, daemon_id: str) -> Optional[Daemon]:
        """Get a specific daemon record."""
        return await db.get(Daemon, daemon_id)

    async def start_daemon(self, daemon_id: str) -> None:
        """Start a daemon."""
        # Check if already running
        if daemon_id in self._daemons:
            raise ValueError(f"Daemon {daemon_id} is already running")

        # Get daemon record
        async with AsyncSessionLocal() as db:
            daemon_record = await db.get(Daemon, daemon_id)
            if not daemon_record:
                raise ValueError(f"Daemon {daemon_id} not found")

            # Get daemon class
            daemon_classes = get_daemon_classes()
            daemon_type = DaemonType(daemon_record.type)
            daemon_class = daemon_classes.get(daemon_type)

            if not daemon_class:
                raise ValueError(f"Unknown daemon type: {daemon_record.type}")

            # Create and start daemon instance
            daemon = daemon_class(
                daemon_id=daemon_id, config=daemon_record.configuration or {}
            )

            await daemon.start()
            self._daemons[daemon_id] = daemon

            logger.info(f"Started daemon {daemon_record.name} ({daemon_id})")

    async def stop_daemon(self, daemon_id: str) -> None:
        """Stop a daemon."""
        daemon = self._daemons.get(daemon_id)
        if not daemon:
            raise ValueError(f"Daemon {daemon_id} is not running")

        await daemon.stop()
        del self._daemons[daemon_id]

        logger.info(f"Stopped daemon {daemon_id}")

    async def restart_daemon(self, daemon_id: str) -> None:
        """Restart a daemon."""
        # Stop if running
        if daemon_id in self._daemons:
            await self.stop_daemon(daemon_id)

        # Start again
        await self.start_daemon(daemon_id)

    async def update_daemon_config(
        self,
        db: AsyncSession,
        daemon_id: str,
        config: Dict[str, Any],
        enabled: Optional[bool] = None,
        auto_start: Optional[bool] = None,
    ) -> Daemon:
        """Update daemon configuration."""
        daemon_record = await db.get(Daemon, daemon_id)
        if not daemon_record:
            raise ValueError(f"Daemon {daemon_id} not found")

        # Use setattr to properly update SQLAlchemy model attributes
        setattr(daemon_record, "configuration", config)
        if enabled is not None:
            setattr(daemon_record, "enabled", enabled)
        if auto_start is not None:
            setattr(daemon_record, "auto_start", auto_start)

        setattr(daemon_record, "updated_at", datetime.now(timezone.utc))
        await db.commit()

        # If daemon is running, it will pick up new config on restart

        return daemon_record

    async def get_daemon_logs(
        self,
        db: AsyncSession,
        daemon_id: str,
        limit: int = 100,
        level: Optional[LogLevel] = None,
        since: Optional[datetime] = None,
    ) -> List[DaemonLog]:
        """Get daemon logs with optional filtering."""
        query = select(DaemonLog).where(DaemonLog.daemon_id == daemon_id)

        if level:
            query = query.where(DaemonLog.level == level.value)

        if since:
            query = query.where(DaemonLog.created_at >= since)

        query = query.order_by(desc(DaemonLog.created_at)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_daemon_job_history(
        self,
        db: AsyncSession,
        daemon_id: str,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[DaemonJobHistory]:
        """Get daemon job history."""
        query = select(DaemonJobHistory).where(DaemonJobHistory.daemon_id == daemon_id)

        if since:
            query = query.where(DaemonJobHistory.created_at >= since)

        query = query.order_by(desc(DaemonJobHistory.created_at)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def check_daemon_health(self, db: AsyncSession) -> Dict[str, Any]:
        """Check health of all daemons."""
        health_status: Dict[str, Any] = {"healthy": [], "unhealthy": [], "stopped": []}

        daemons = await self.get_all_daemons(db)

        for daemon in daemons:
            daemon_id = str(daemon.id)

            # Check if daemon should be running
            if daemon.enabled:
                # Check if actually running
                if daemon_id in self._daemons:
                    # Check heartbeat
                    if daemon.last_heartbeat:
                        time_since_heartbeat = (
                            datetime.now(timezone.utc) - daemon.last_heartbeat
                        )
                        if time_since_heartbeat < timedelta(minutes=2):
                            health_status["healthy"].append(
                                {
                                    "id": daemon_id,
                                    "name": daemon.name,
                                    "uptime": self._daemons[
                                        daemon_id
                                    ].get_uptime_seconds(),
                                }
                            )
                        else:
                            health_status["unhealthy"].append(
                                {
                                    "id": daemon_id,
                                    "name": daemon.name,
                                    "reason": "No recent heartbeat",
                                    "last_heartbeat": daemon.last_heartbeat.isoformat(),
                                }
                            )
                    else:
                        health_status["unhealthy"].append(
                            {
                                "id": daemon_id,
                                "name": daemon.name,
                                "reason": "No heartbeat recorded",
                            }
                        )
                else:
                    health_status["unhealthy"].append(
                        {
                            "id": daemon_id,
                            "name": daemon.name,
                            "reason": "Should be running but is not",
                        }
                    )
            else:
                health_status["stopped"].append({"id": daemon_id, "name": daemon.name})

        return health_status

    def get_running_daemons(self) -> List[str]:
        """Get list of currently running daemon IDs."""
        return list(self._daemons.keys())

    def is_daemon_running(self, daemon_id: str) -> bool:
        """Check if a specific daemon is running."""
        return daemon_id in self._daemons


# Global daemon service instance
daemon_service = DaemonService()
