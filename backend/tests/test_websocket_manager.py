"""Tests for WebSocket manager."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.services.websocket_manager import WebSocketManager, get_websocket_manager


class TestWebSocketManager:
    """Test WebSocket management functionality."""

    @pytest.fixture
    def manager(self):
        """Create WebSocket manager instance."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"type": "ping"}')
        ws.client_state = WebSocketState.CONNECTED
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        await manager.connect(mock_websocket)

        assert mock_websocket in manager.active_connections
        assert mock_websocket in manager.connection_metadata
        assert "subscriptions" in manager.connection_metadata[mock_websocket]
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        # Setup connection
        manager.active_connections.append(mock_websocket)
        manager.connection_metadata[mock_websocket] = {"subscriptions": set()}

        await manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.active_connections
        assert mock_websocket not in manager.connection_metadata

    @pytest.mark.asyncio
    async def test_disconnect_with_subscriptions(self, manager, mock_websocket):
        """Test disconnecting removes subscriptions."""
        # Setup connection with subscriptions
        manager.active_connections.append(mock_websocket)
        manager.connection_metadata[mock_websocket] = {
            "subscriptions": {"job1", "job2"}
        }
        manager.job_subscriptions["job1"].add(mock_websocket)
        manager.job_subscriptions["job2"].add(mock_websocket)

        await manager.disconnect(mock_websocket)

        # Verify websocket removed from subscriptions and empty sets cleaned up
        assert "job1" not in manager.job_subscriptions  # Cleaned up empty set
        assert "job2" not in manager.job_subscriptions  # Cleaned up empty set

    @pytest.mark.asyncio
    async def test_subscribe_to_job(self, manager, mock_websocket):
        """Test subscribing to job updates."""
        manager.connection_metadata[mock_websocket] = {"subscriptions": set()}
        job_id = "job123"

        await manager.subscribe_to_job(mock_websocket, job_id)

        assert mock_websocket in manager.job_subscriptions[job_id]
        assert job_id in manager.connection_metadata[mock_websocket]["subscriptions"]

    @pytest.mark.asyncio
    async def test_unsubscribe_from_job(self, manager, mock_websocket):
        """Test unsubscribing from job updates."""
        job_id = "job123"
        manager.connection_metadata[mock_websocket] = {"subscriptions": {job_id}}
        manager.job_subscriptions[job_id].add(mock_websocket)

        await manager.unsubscribe_from_job(mock_websocket, job_id)

        assert mock_websocket not in manager.job_subscriptions.get(job_id, set())
        assert (
            job_id not in manager.connection_metadata[mock_websocket]["subscriptions"]
        )

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending message to specific client."""
        message = "Hello client"

        await manager.send_personal_message(message, mock_websocket)

        mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_disconnected(self, manager, mock_websocket):
        """Test sending message to disconnected client."""
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        manager.disconnect = AsyncMock()

        await manager.send_personal_message("test", mock_websocket)

        mock_websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_personal_json(self, manager, mock_websocket):
        """Test sending JSON to specific client."""
        data = {"type": "update", "value": 123}

        await manager.send_personal_json(data, mock_websocket)

        mock_websocket.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all clients."""
        # Create multiple mock connections
        mock_ws1 = Mock(spec=WebSocket)
        mock_ws1.send_text = AsyncMock()
        mock_ws1.client_state = WebSocketState.CONNECTED

        mock_ws2 = Mock(spec=WebSocket)
        mock_ws2.send_text = AsyncMock()
        mock_ws2.client_state = WebSocketState.CONNECTED

        manager.active_connections = [mock_ws1, mock_ws2]

        message = "Broadcast message"

        await manager.broadcast(message)

        mock_ws1.send_text.assert_called_once_with(message)
        mock_ws2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_handles_errors(self, manager, mock_websocket):
        """Test broadcast handles send errors."""
        mock_websocket.send_text.side_effect = Exception("Send failed")
        manager.active_connections = [mock_websocket]
        manager.disconnect = AsyncMock()

        await manager.broadcast("test")

        manager.disconnect.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_broadcast_json(self, manager):
        """Test broadcasting JSON data."""
        mock_ws = Mock(spec=WebSocket)
        mock_ws.send_text = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        manager.active_connections = [mock_ws]

        data = {"type": "notification", "message": "test"}

        await manager.broadcast_json(data)

        mock_ws.send_text.assert_called_once_with(json.dumps(data))

    @pytest.mark.asyncio
    async def test_send_job_update(self, manager, mock_websocket):
        """Test sending job update to subscribers."""
        job_id = "job123"
        manager.job_subscriptions[job_id].add(mock_websocket)

        update = {"progress": 50, "status": "running"}

        await manager.send_job_update(job_id, update)

        expected_data = {"type": "job_update", "job_id": job_id, **update}
        mock_websocket.send_json.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_send_job_update_no_subscribers(self, manager):
        """Test sending job update with no subscribers."""
        # Should not raise exception
        await manager.send_job_update("job999", {"status": "done"})

    @pytest.mark.asyncio
    async def test_send_job_progress(self, manager, mock_websocket):
        """Test sending job progress update."""
        job_id = "job123"
        manager.job_subscriptions[job_id].add(mock_websocket)

        await manager.send_job_progress(job_id, 75.5, "Processing...")

        expected_data = {
            "type": "job_update",
            "job_id": job_id,
            "progress": 75.5,
            "message": "Processing...",
        }
        mock_websocket.send_json.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_send_job_completed(self, manager, mock_websocket):
        """Test sending job completion notification."""
        job_id = "job123"
        manager.job_subscriptions[job_id].add(mock_websocket)
        result = {"scenes_processed": 10}

        await manager.send_job_completed(job_id, result)

        expected_data = {
            "type": "job_update",
            "job_id": job_id,
            "status": "completed",
            "result": result,
        }
        mock_websocket.send_json.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_send_job_failed(self, manager, mock_websocket):
        """Test sending job failure notification."""
        job_id = "job123"
        manager.job_subscriptions[job_id].add(mock_websocket)
        error = "Connection timeout"

        await manager.send_job_failed(job_id, error)

        expected_data = {
            "type": "job_update",
            "job_id": job_id,
            "status": "failed",
            "error": error,
        }
        mock_websocket.send_json.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_cleanup_disconnected_during_job_update(self, manager):
        """Test cleanup of disconnected clients during job update."""
        job_id = "job123"

        # Create disconnected websocket
        mock_ws = Mock(spec=WebSocket)
        mock_ws.client_state = WebSocketState.DISCONNECTED
        mock_ws.send_json = AsyncMock()

        manager.job_subscriptions[job_id].add(mock_ws)
        manager.disconnect = AsyncMock()
        manager.unsubscribe_from_job = AsyncMock()

        await manager.send_job_update(job_id, {"status": "test"})

        manager.unsubscribe_from_job.assert_called_once_with(mock_ws, job_id)
        manager.disconnect.assert_called_once_with(mock_ws)

    def test_get_websocket_manager(self):
        """Test getting global websocket manager instance."""
        manager = get_websocket_manager()
        assert isinstance(manager, WebSocketManager)
        # Should return same instance
        assert manager is get_websocket_manager()
