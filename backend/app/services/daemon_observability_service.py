"""Service for tracking daemon observability metrics, errors, and activities."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daemon import (
    Daemon,
    DaemonJobAction,
    DaemonJobHistory,
    DaemonLog,
    LogLevel,
)
from app.models.daemon_observability import (
    ActivityType,
    AlertType,
    DaemonActivity,
    DaemonAlert,
    DaemonError,
    DaemonMetric,
    DaemonStatus,
    ErrorType,
)
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class DaemonObservabilityService:
    """Service for tracking and managing daemon observability."""

    async def track_error(
        self,
        db: AsyncSession,
        daemon_id: UUID,
        error_type: ErrorType,
        error_message: str,
        error_details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DaemonError:
        """Track a daemon error, updating existing or creating new."""
        # Check if similar error exists (unresolved)
        result = await db.execute(
            select(DaemonError).where(
                and_(
                    DaemonError.daemon_id == daemon_id,
                    DaemonError.error_type == error_type.value,
                    DaemonError.error_message == error_message,
                    DaemonError.resolved.is_(False),
                )
            )
        )
        existing_error = result.scalar_one_or_none()

        if existing_error:
            # Update existing error
            existing_error.occurrence_count += 1  # type: ignore
            existing_error.last_seen = datetime.now(timezone.utc)  # type: ignore
            existing_error.error_details = error_details or existing_error.error_details  # type: ignore
            if context:
                existing_error.context = context  # type: ignore
            await db.commit()
            error = existing_error
        else:
            # Create new error
            error = DaemonError(
                daemon_id=daemon_id,
                error_type=error_type.value,
                error_message=error_message,
                error_details=error_details,
                context=context,
            )
            db.add(error)
            await db.commit()

        # Update daemon status
        await self._update_daemon_status_error(db, daemon_id, error_message)

        # Track as activity
        await self.track_activity(
            db,
            daemon_id,
            ActivityType.ERROR_OCCURRED,
            f"Error: {error_message}",
            details={"error_id": str(error.id), "error_type": error_type.value},
            severity="error",
        )

        # Check alerts
        await self._check_error_alerts(db, daemon_id)

        return error

    async def track_activity(
        self,
        db: AsyncSession,
        daemon_id: UUID,
        activity_type: ActivityType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> DaemonActivity:
        """Track a daemon activity."""
        activity = DaemonActivity(
            daemon_id=daemon_id,
            activity_type=activity_type.value,
            message=message,
            details=details,
            severity=severity,
        )
        db.add(activity)
        await db.commit()

        # Broadcast activity
        await websocket_manager.broadcast_daemon_activity(
            daemon_id=str(daemon_id), activity=activity.to_dict()
        )

        return activity

    async def track_metric(
        self,
        db: AsyncSession,
        daemon_id: UUID,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
    ) -> DaemonMetric:
        """Track a daemon metric."""
        metric = DaemonMetric(
            daemon_id=daemon_id,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
        )
        db.add(metric)
        await db.commit()
        return metric

    async def update_daemon_status(
        self,
        db: AsyncSession,
        daemon_id: UUID,
        current_activity: Optional[str] = None,
        current_progress: Optional[float] = None,
        items_processed: Optional[int] = None,
        items_pending: Optional[int] = None,
    ) -> DaemonStatus:
        """Update daemon status information."""
        result = await db.execute(
            select(DaemonStatus).where(DaemonStatus.daemon_id == daemon_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            status = DaemonStatus(daemon_id=daemon_id)
            db.add(status)

        if current_activity is not None:
            status.current_activity = current_activity  # type: ignore
        if current_progress is not None:
            status.current_progress = min(100.0, max(0.0, current_progress))  # type: ignore
        if items_processed is not None:
            status.items_processed = items_processed  # type: ignore
        if items_pending is not None:
            status.items_pending = items_pending  # type: ignore

        status.updated_at = datetime.now(timezone.utc)  # type: ignore
        await db.commit()

        # Broadcast status update
        await websocket_manager.broadcast_daemon_status(
            daemon_id=str(daemon_id), status=status.to_dict()
        )

        return status

    async def calculate_daemon_statistics(
        self, db: AsyncSession, daemon_id: UUID
    ) -> Dict[str, Any]:
        """Calculate comprehensive daemon statistics."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)

        # Get or create status
        result = await db.execute(
            select(DaemonStatus).where(DaemonStatus.daemon_id == daemon_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            status = DaemonStatus(daemon_id=daemon_id)
            db.add(status)

        # Count errors in last 24h
        error_count_result = await db.execute(
            select(func.count(DaemonError.id)).where(
                and_(
                    DaemonError.daemon_id == daemon_id,
                    DaemonError.last_seen >= last_24h,
                )
            )
        )
        status.error_count_24h = error_count_result.scalar() or 0  # type: ignore

        # Count warnings in last 24h
        warning_count_result = await db.execute(
            select(func.count(DaemonLog.id)).where(
                and_(
                    DaemonLog.daemon_id == daemon_id,
                    DaemonLog.level == LogLevel.WARNING.value,
                    DaemonLog.created_at >= last_24h,
                )
            )
        )
        status.warning_count_24h = warning_count_result.scalar() or 0  # type: ignore

        # Count jobs in last 24h
        job_stats = await db.execute(
            select(
                DaemonJobHistory.action,
                func.count(DaemonJobHistory.id).label("count"),
            )
            .where(
                and_(
                    DaemonJobHistory.daemon_id == daemon_id,
                    DaemonJobHistory.created_at >= last_24h,
                )
            )
            .group_by(DaemonJobHistory.action)
        )

        job_counts = {row[0]: row[1] for row in job_stats}
        status.jobs_launched_24h = job_counts.get(DaemonJobAction.LAUNCHED.value, 0)  # type: ignore
        status.jobs_completed_24h = job_counts.get(DaemonJobAction.FINISHED.value, 0)  # type: ignore
        status.jobs_failed_24h = job_counts.get(DaemonJobAction.CANCELLED.value, 0)  # type: ignore

        # Calculate average job duration (simplified - would need job table for accurate calculation)
        # For now, we'll just note that this is a placeholder for future enhancement

        # Calculate health score
        status.health_score = await self._calculate_health_score(db, daemon_id, status)  # type: ignore

        # Calculate uptime percentage
        daemon = await db.get(Daemon, daemon_id)
        if daemon and daemon.started_at:
            uptime = (now - daemon.started_at).total_seconds()
            expected_uptime = 86400  # 24 hours in seconds
            status.uptime_percentage = min(100.0, (uptime / expected_uptime) * 100)  # type: ignore
        else:
            status.uptime_percentage = 0.0  # type: ignore

        await db.commit()

        return status.to_dict()

    async def get_daemon_errors(
        self,
        db: AsyncSession,
        daemon_id: UUID,
        limit: int = 10,
        unresolved_only: bool = True,
    ) -> List[DaemonError]:
        """Get daemon errors."""
        query = select(DaemonError).where(DaemonError.daemon_id == daemon_id)

        if unresolved_only:
            query = query.where(DaemonError.resolved.is_(False))

        query = query.order_by(desc(DaemonError.last_seen)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_recent_activities(
        self,
        db: AsyncSession,
        daemon_id: Optional[UUID] = None,
        limit: int = 50,
        severity: Optional[str] = None,
    ) -> List[DaemonActivity]:
        """Get recent daemon activities."""
        query = select(DaemonActivity)

        if daemon_id:
            query = query.where(DaemonActivity.daemon_id == daemon_id)

        if severity:
            query = query.where(DaemonActivity.severity == severity)

        query = query.order_by(desc(DaemonActivity.created_at)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_daemon_metrics(
        self,
        db: AsyncSession,
        daemon_id: UUID,
        metric_name: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DaemonMetric]:
        """Get daemon metrics."""
        query = select(DaemonMetric).where(DaemonMetric.daemon_id == daemon_id)

        if metric_name:
            query = query.where(DaemonMetric.metric_name == metric_name)

        if since:
            query = query.where(DaemonMetric.timestamp >= since)

        query = query.order_by(desc(DaemonMetric.timestamp)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def resolve_error(
        self, db: AsyncSession, error_id: UUID
    ) -> Optional[DaemonError]:
        """Mark an error as resolved."""
        error = await db.get(DaemonError, error_id)
        if error:
            error.resolved = True  # type: ignore
            error.resolved_at = datetime.now(timezone.utc)  # type: ignore
            await db.commit()
        return error

    async def _update_daemon_status_error(
        self, db: AsyncSession, daemon_id: UUID, error_message: str
    ) -> None:
        """Update daemon status with error information."""
        result = await db.execute(
            select(DaemonStatus).where(DaemonStatus.daemon_id == daemon_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            status = DaemonStatus(daemon_id=daemon_id)
            db.add(status)

        status.last_error_message = error_message[:500]  # type: ignore  # Truncate if too long
        status.last_error_time = datetime.now(timezone.utc)  # type: ignore
        await db.commit()

    async def _calculate_health_score(
        self, db: AsyncSession, daemon_id: UUID, status: DaemonStatus
    ) -> float:
        """Calculate daemon health score (0-100)."""
        score = 100.0

        # Deduct for errors (max -40)
        if status.error_count_24h > 0:
            error_penalty = min(40, int(status.error_count_24h * 5))
            score -= error_penalty

        # Deduct for warnings (max -20)
        if status.warning_count_24h > 0:
            warning_penalty = min(20, int(status.warning_count_24h * 2))
            score -= warning_penalty

        # Deduct for failed jobs (max -30)
        if status.jobs_launched_24h > 0:
            failure_rate = status.jobs_failed_24h / status.jobs_launched_24h
            job_penalty = min(30, int(failure_rate * 30))
            score -= job_penalty

        # Deduct for low uptime (max -10)
        if status.uptime_percentage < 95:
            uptime_penalty = min(10, int((95 - status.uptime_percentage) / 5))
            score -= uptime_penalty

        return max(0.0, score)

    async def _check_error_alerts(self, db: AsyncSession, daemon_id: UUID) -> None:
        """Check if any error alerts should be triggered."""
        # Get error count in last 10 minutes
        ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
        error_count_result = await db.execute(
            select(func.count(DaemonError.id)).where(
                and_(
                    DaemonError.daemon_id == daemon_id,
                    DaemonError.last_seen >= ten_min_ago,
                )
            )
        )
        error_count = error_count_result.scalar() or 0

        # Check error threshold alert
        alert_result = await db.execute(
            select(DaemonAlert).where(
                and_(
                    DaemonAlert.daemon_id == daemon_id,
                    DaemonAlert.alert_type == AlertType.ERROR_THRESHOLD.value,
                    DaemonAlert.enabled.is_(True),
                )
            )
        )
        alert = alert_result.scalar_one_or_none()

        if alert and alert.threshold_value and error_count >= alert.threshold_value:
            # Trigger alert
            alert.last_triggered = datetime.now(timezone.utc)  # type: ignore
            alert.trigger_count += 1  # type: ignore
            await db.commit()

            # Send notification (implement based on notification_method)
            await self._send_alert_notification(
                alert, f"Error threshold exceeded: {error_count} errors in 10 minutes"
            )

    async def _send_alert_notification(self, alert: DaemonAlert, message: str) -> None:
        """Send alert notification based on configured method."""
        # For now, just broadcast to UI
        if alert.notification_method == "UI":
            await websocket_manager.broadcast_daemon_alert(
                daemon_id=str(alert.daemon_id),
                alert={
                    "alert_type": alert.alert_type,
                    "message": message,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        # TODO: Implement email and webhook notifications


# Create singleton instance
daemon_observability_service = DaemonObservabilityService()
