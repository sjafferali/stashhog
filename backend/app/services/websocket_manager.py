"""
WebSocket manager for real-time updates.
"""

import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    """

    def __init__(self) -> None:
        # Store active connections
        self.active_connections: List[WebSocket] = []

        # Store job subscriptions
        self.job_subscriptions: Dict[str, Set[WebSocket]] = defaultdict(set)

        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}

        # Store daemon subscriptions
        self.daemon_subscriptions: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "connected_at": None,  # Add timestamp if needed
            "subscriptions": set(),
        }
        logger.info("WebSocket client connected")

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from all subscriptions
        for job_id in list(self.job_subscriptions.keys()):
            if websocket in self.job_subscriptions[job_id]:
                self.job_subscriptions[job_id].discard(websocket)
                if not self.job_subscriptions[job_id]:
                    del self.job_subscriptions[job_id]

        # Remove from daemon subscriptions
        for daemon_id in list(self.daemon_subscriptions.keys()):
            if websocket in self.daemon_subscriptions[daemon_id]:
                self.daemon_subscriptions[daemon_id].discard(websocket)
                if not self.daemon_subscriptions[daemon_id]:
                    del self.daemon_subscriptions[daemon_id]

        # Clean up metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        logger.info("WebSocket client disconnected")

    async def subscribe_to_job(self, websocket: WebSocket, job_id: str) -> None:
        """
        Subscribe a WebSocket to job updates.
        """
        self.job_subscriptions[job_id].add(websocket)
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(job_id)
        logger.info(f"WebSocket subscribed to job {job_id}")

    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: str) -> None:
        """
        Unsubscribe a WebSocket from job updates.
        """
        if job_id in self.job_subscriptions:
            self.job_subscriptions[job_id].discard(websocket)
            if not self.job_subscriptions[job_id]:
                del self.job_subscriptions[job_id]

        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(job_id)

        logger.info(f"WebSocket unsubscribed from job {job_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """
        Send a message to a specific WebSocket.
        """
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                await self.disconnect(websocket)

    async def send_personal_json(self, data: dict, websocket: WebSocket) -> None:
        """
        Send JSON data to a specific WebSocket.
        """
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending JSON: {e}")
                await self.disconnect(websocket)

    async def broadcast(self, message: str) -> None:
        """
        Broadcast a message to all connected clients.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_json(self, data: dict) -> None:
        """
        Broadcast JSON data to all connected clients.
        """
        await self.broadcast(json.dumps(data))

    async def send_job_update(self, job_id: str, update: dict) -> None:
        """
        Send job update to all subscribers.
        """
        if job_id not in self.job_subscriptions:
            return

        disconnected = []
        for websocket in self.job_subscriptions[job_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(
                        {"type": "job_update", "job_id": job_id, **update}
                    )
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending job update: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unsubscribe_from_job(websocket, job_id)
            await self.disconnect(websocket)

    async def send_job_progress(
        self, job_id: str, progress: float, message: Optional[str] = None
    ) -> None:
        """
        Send job progress update.
        """
        await self.send_job_update(job_id, {"progress": progress, "message": message})

    async def send_job_completed(
        self, job_id: str, result: Optional[dict] = None
    ) -> None:
        """
        Send job completion notification.
        """
        await self.send_job_update(job_id, {"status": "completed", "result": result})

    async def send_job_failed(self, job_id: str, error: str) -> None:
        """
        Send job failure notification.
        """
        await self.send_job_update(job_id, {"status": "failed", "error": error})

    async def broadcast_job_update(self, job: dict) -> None:
        """
        Broadcast job update to all connected clients (for the general jobs WebSocket).
        """
        update_data = {"type": "job_update", "job": job}
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(update_data)
                else:
                    disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting job update: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def subscribe_to_daemon(self, websocket: WebSocket, daemon_id: str) -> None:
        """
        Subscribe a WebSocket to daemon updates.
        """
        logger.info(
            f"subscribe_to_daemon called with daemon_id: {daemon_id} (type: {type(daemon_id)})"
        )
        self.daemon_subscriptions[daemon_id].add(websocket)
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(
                f"daemon:{daemon_id}"
            )
        logger.info(f"WebSocket subscribed to daemon {daemon_id}")
        logger.info(
            f"Current daemon subscriptions after subscribe: {list(self.daemon_subscriptions.keys())}"
        )

    async def unsubscribe_from_daemon(
        self, websocket: WebSocket, daemon_id: str
    ) -> None:
        """
        Unsubscribe a WebSocket from daemon updates.
        """
        if daemon_id in self.daemon_subscriptions:
            self.daemon_subscriptions[daemon_id].discard(websocket)
            if not self.daemon_subscriptions[daemon_id]:
                del self.daemon_subscriptions[daemon_id]

        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(
                f"daemon:{daemon_id}"
            )

        logger.info(f"WebSocket unsubscribed from daemon {daemon_id}")

    async def broadcast_daemon_log(self, daemon_id: str, log: dict) -> None:
        """
        Broadcast daemon log to all subscribers.
        """
        logger.info(f"Broadcasting daemon log for daemon_id: {daemon_id}")
        logger.info(
            f"Current daemon subscriptions: {list(self.daemon_subscriptions.keys())}"
        )
        logger.info(
            f"Number of subscribers for daemon {daemon_id}: {len(self.daemon_subscriptions.get(daemon_id, set()))}"
        )

        if daemon_id not in self.daemon_subscriptions:
            logger.warning(f"No subscribers for daemon {daemon_id}")
            return

        disconnected = []
        message = {"type": "daemon_log", "daemon_id": daemon_id, "log": log}
        logger.info(f"Broadcasting message: {message}")

        for websocket in self.daemon_subscriptions[daemon_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    logger.info(f"Sending daemon log to WebSocket: {websocket}")
                    await websocket.send_json(message)
                    logger.info("Successfully sent daemon log message")
                else:
                    logger.warning(f"WebSocket not connected: {websocket}")
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending daemon log: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unsubscribe_from_daemon(websocket, daemon_id)
            await self.disconnect(websocket)

    async def broadcast_daemon_status(self, daemon_id: str, status: dict) -> None:
        """
        Broadcast daemon status update to all subscribers.
        """
        if daemon_id not in self.daemon_subscriptions:
            return

        disconnected = []
        message = {"type": "daemon_status", "daemon_id": daemon_id, "status": status}

        for websocket in self.daemon_subscriptions[daemon_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending daemon status: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unsubscribe_from_daemon(websocket, daemon_id)
            await self.disconnect(websocket)

    async def broadcast_daemon_job_action(self, daemon_id: str, action: dict) -> None:
        """
        Broadcast daemon job action to all subscribers.
        """
        if daemon_id not in self.daemon_subscriptions:
            return

        disconnected = []
        message = {
            "type": "daemon_job_action",
            "daemon_id": daemon_id,
            "action": action,
        }

        for websocket in self.daemon_subscriptions[daemon_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending daemon job action: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unsubscribe_from_daemon(websocket, daemon_id)
            await self.disconnect(websocket)

    async def broadcast_daemon_update(self, daemon: dict) -> None:
        """
        Broadcast daemon update to all connected clients (for the daemons list).
        """
        update_data = {"type": "daemon_update", "daemon": daemon}
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(update_data)
                else:
                    disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting daemon update: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_daemon_activity(self, daemon_id: str, activity: dict) -> None:
        """
        Broadcast daemon activity to all subscribers and main page.
        """
        # Send to daemon-specific subscribers
        if daemon_id in self.daemon_subscriptions:
            disconnected = []
            message = {
                "type": "daemon_activity",
                "daemon_id": daemon_id,
                "activity": activity,
            }

            for websocket in self.daemon_subscriptions[daemon_id]:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(message)
                    else:
                        disconnected.append(websocket)
                except Exception as e:
                    logger.error(f"Error sending daemon activity: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for websocket in disconnected:
                await self.unsubscribe_from_daemon(websocket, daemon_id)
                await self.disconnect(websocket)

        # Also broadcast to all connections for activity feed
        await self.broadcast_to_all({"type": "activity_feed", "activity": activity})

    async def broadcast_daemon_alert(self, daemon_id: str, alert: dict) -> None:
        """
        Broadcast daemon alert to all connections.
        """
        message = {
            "type": "daemon_alert",
            "daemon_id": daemon_id,
            "alert": alert,
        }
        await self.broadcast_to_all(message)

    async def broadcast_to_all(self, message: dict) -> None:
        """
        Broadcast a message to all active connections.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """
    Get the global WebSocket manager instance.
    """
    return websocket_manager
