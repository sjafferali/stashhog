import logging
from datetime import datetime
from typing import List, Optional

from app.services.websocket_manager import WebSocketManager

from .models import SyncError, SyncResult

logger = logging.getLogger(__name__)


class SyncProgress:
    """Handles progress tracking and reporting for sync operations"""

    def __init__(self, job_id: str, total_items: int):
        self.job_id = job_id
        self.total_items = total_items
        self.processed_items = 0
        self.errors: List[SyncError] = []
        self.start_time = datetime.utcnow()
        self.last_update_time = self.start_time
        self.update_interval = 1.0  # Seconds between updates
        self._websocket_manager: Optional[WebSocketManager] = None

    def set_websocket_manager(self, manager: WebSocketManager) -> None:
        """Set the WebSocket manager for real-time updates"""
        self._websocket_manager = manager

    async def update(
        self, processed: int, error: Optional[str] = None, force_update: bool = False
    ) -> None:
        """Update progress and optionally notify via WebSocket"""
        self.processed_items = processed

        if error:
            self.errors.append(
                SyncError(
                    entity_type="unknown", entity_id="unknown", error_message=error
                )
            )

        # Throttle updates unless forced
        now = datetime.utcnow()
        time_since_last = (now - self.last_update_time).total_seconds()

        if not force_update and time_since_last < self.update_interval:
            return

        self.last_update_time = now

        # Send WebSocket update
        await self._send_progress_update()

    async def update_with_details(
        self,
        processed: int,
        entity_type: str,
        entity_id: str,
        action: str,
        error: Optional[str] = None,
    ) -> None:
        """Update progress with detailed information"""
        self.processed_items = processed

        if error:
            self.errors.append(
                SyncError(
                    entity_type=entity_type, entity_id=entity_id, error_message=error
                )
            )

        # Send detailed update
        await self._send_detailed_update(entity_type, entity_id, action)

    async def complete(self, result: SyncResult) -> None:
        """Mark sync as complete and send final update"""
        await self._send_completion_update(result)

    async def _send_progress_update(self) -> None:
        """Send progress update via WebSocket"""
        if not self._websocket_manager:
            return

        progress_data = {
            "type": "sync_progress",
            "job_id": self.job_id,
            "progress": {
                "processed": self.processed_items,
                "total": self.total_items,
                "percentage": self._calculate_percentage(),
                "elapsed_seconds": self._calculate_elapsed_seconds(),
                "estimated_remaining_seconds": self._estimate_remaining_seconds(),
                "errors": len(self.errors),
            },
        }

        try:
            await self._websocket_manager.broadcast_json(progress_data)
        except Exception as e:
            logger.error(f"Failed to send WebSocket update: {str(e)}")

    async def _send_detailed_update(
        self, entity_type: str, entity_id: str, action: str
    ) -> None:
        """Send detailed update about specific entity"""
        if not self._websocket_manager:
            return

        detail_data = {
            "type": "sync_detail",
            "job_id": self.job_id,
            "detail": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "progress": {
                "processed": self.processed_items,
                "total": self.total_items,
                "percentage": self._calculate_percentage(),
            },
        }

        try:
            await self._websocket_manager.broadcast_json(detail_data)
        except Exception as e:
            logger.error(f"Failed to send detailed WebSocket update: {str(e)}")

    async def _send_completion_update(self, result: SyncResult) -> None:
        """Send completion notification"""
        if not self._websocket_manager:
            return

        completion_data = {
            "type": "sync_complete",
            "job_id": self.job_id,
            "result": {
                "status": result.status.value,
                "total_items": result.total_items,
                "processed_items": result.processed_items,
                "created_items": result.created_items,
                "updated_items": result.updated_items,
                "skipped_items": result.skipped_items,
                "failed_items": result.failed_items,
                "duration_seconds": result.duration_seconds,
                "success_rate": result.success_rate,
                "errors": [
                    {
                        "entity_type": e.entity_type,
                        "entity_id": e.entity_id,
                        "error": e.error_message,
                    }
                    for e in result.errors[:10]  # Limit to first 10 errors
                ],
            },
        }

        try:
            await self._websocket_manager.broadcast_json(completion_data)
        except Exception as e:
            logger.error(f"Failed to send completion WebSocket update: {str(e)}")

    def _calculate_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 100.0
        return min(100.0, (self.processed_items / self.total_items) * 100)

    def _calculate_elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def _estimate_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time based on current progress"""
        if self.processed_items == 0:
            return None

        elapsed = self._calculate_elapsed_seconds()
        rate = self.processed_items / elapsed  # Items per second

        if rate == 0:
            return None

        remaining_items = self.total_items - self.processed_items
        return remaining_items / rate


class BatchProgress:
    """Progress tracker for batch operations"""

    def __init__(self, job_id: str, batch_size: int):
        self.job_id = job_id
        self.batch_size = batch_size
        self.current_batch = 0
        self.items_in_batch = 0
        self.total_processed = 0

    def start_batch(self, batch_number: int) -> None:
        """Start tracking a new batch"""
        self.current_batch = batch_number
        self.items_in_batch = 0

    def increment(self) -> None:
        """Increment progress within current batch"""
        self.items_in_batch += 1
        self.total_processed += 1

    def complete_batch(self) -> None:
        """Mark current batch as complete"""
        logger.info(
            f"Completed batch {self.current_batch}: "
            f"{self.items_in_batch} items processed "
            f"(total: {self.total_processed})"
        )
