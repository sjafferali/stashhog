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


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """
    Get the global WebSocket manager instance.
    """
    return websocket_manager
