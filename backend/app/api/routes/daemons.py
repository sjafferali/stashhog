"""
API routes for daemon management.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.daemon import LogLevel
from app.schemas.daemon import (
    DaemonHealthItem,
    DaemonHealthResponse,
    DaemonJobHistoryResponse,
    DaemonLogResponse,
    DaemonResponse,
    DaemonUpdateRequest,
)
from app.services.daemon_observability_service import daemon_observability_service
from app.services.daemon_service import daemon_service
from app.services.websocket_manager import (
    WebSocketManager,
    get_websocket_manager,
    websocket_manager,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[DaemonResponse])
async def get_daemons(db: AsyncSession = Depends(get_async_db)):
    """Get all daemons."""
    daemons = await daemon_service.get_all_daemons(db)
    # Use to_dict() which already converts UUID to string
    return [daemon.to_dict() for daemon in daemons]


@router.get("/health/check", response_model=DaemonHealthResponse)
async def check_daemon_health(db: AsyncSession = Depends(get_async_db)):
    """Check health of all daemons."""
    health_status = await daemon_service.check_daemon_health(db)

    # Convert dictionaries to DaemonHealthItem objects
    return DaemonHealthResponse(
        healthy=[DaemonHealthItem(**item) for item in health_status["healthy"]],
        unhealthy=[DaemonHealthItem(**item) for item in health_status["unhealthy"]],
        stopped=[DaemonHealthItem(**item) for item in health_status["stopped"]],
    )


async def _handle_daemon_subscribe(
    websocket: WebSocket, daemon_id: str, manager: WebSocketManager
) -> None:
    """Handle daemon subscription command."""
    await manager.subscribe_to_daemon(websocket, daemon_id)
    await websocket.send_json(
        {"type": "subscription_confirmed", "daemon_id": daemon_id}
    )


async def _handle_daemon_unsubscribe(
    websocket: WebSocket, daemon_id: str, manager: WebSocketManager
) -> None:
    """Handle daemon unsubscription command."""
    await manager.unsubscribe_from_daemon(websocket, daemon_id)
    await websocket.send_json(
        {"type": "unsubscription_confirmed", "daemon_id": daemon_id}
    )


async def _handle_websocket_message(
    websocket: WebSocket, data: Dict[str, Any], manager: WebSocketManager
) -> None:
    """Handle incoming WebSocket message."""
    message_type = data.get("type")
    command = data.get("command")
    daemon_id = data.get("daemon_id")

    # Only log non-ping/pong messages to avoid log spam
    if message_type not in ("ping", "pong"):
        logger.info(f"Received WebSocket message: {data}")

    # Handle ping/pong for keepalive
    if message_type == "ping":
        await websocket.send_json({"type": "pong"})
    elif message_type == "pong":
        # Client responded to our ping
        pass
    # Handle daemon commands
    elif command == "subscribe" and daemon_id:
        logger.info(f"Handling subscribe command for daemon_id: {daemon_id}")
        await _handle_daemon_subscribe(websocket, daemon_id, manager)
    elif command == "unsubscribe" and daemon_id:
        logger.info(f"Handling unsubscribe command for daemon_id: {daemon_id}")
        await _handle_daemon_unsubscribe(websocket, daemon_id, manager)
    elif command:
        logger.warning(f"Invalid command received: {command}")
        await websocket.send_json({"type": "error", "message": "Invalid command"})


@router.websocket("/ws")
async def daemon_websocket(
    websocket: WebSocket,
    manager: WebSocketManager = Depends(get_websocket_manager),
):
    """
    WebSocket for real-time updates of all daemons.
    """
    await manager.connect(websocket)
    logger.info("Client connected to daemons WebSocket")

    try:
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_json()

                # Handle messages
                await _handle_websocket_message(websocket, data, manager)

            except WebSocketDisconnect:
                logger.info("Client disconnected from daemons WebSocket")
                break
            except Exception as e:
                logger.error(f"Daemons WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"Daemons WebSocket error: {str(e)}")
    finally:
        await manager.disconnect(websocket)


@router.get("/{daemon_id}", response_model=DaemonResponse)
async def get_daemon(daemon_id: str, db: AsyncSession = Depends(get_async_db)):
    """Get a specific daemon."""
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")
    return daemon.to_dict()


@router.post("/{daemon_id}/start")
async def start_daemon(daemon_id: str, db: AsyncSession = Depends(get_async_db)):
    """Start a daemon."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    # Check if already running
    if daemon_service.is_daemon_running(daemon_id):
        raise HTTPException(status_code=400, detail="Daemon is already running")

    try:
        await daemon_service.start_daemon(daemon_id)

        # Broadcast status update
        await websocket_manager.broadcast_daemon_update(daemon.to_dict())

        return {"message": f"Daemon {daemon.name} started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{daemon_id}/stop")
async def stop_daemon(daemon_id: str, db: AsyncSession = Depends(get_async_db)):
    """Stop a daemon."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    # Check if running
    if not daemon_service.is_daemon_running(daemon_id):
        raise HTTPException(status_code=400, detail="Daemon is not running")

    try:
        await daemon_service.stop_daemon(daemon_id)

        # Broadcast status update
        await websocket_manager.broadcast_daemon_update(daemon.to_dict())

        return {"message": f"Daemon {daemon.name} stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{daemon_id}/restart")
async def restart_daemon(daemon_id: str, db: AsyncSession = Depends(get_async_db)):
    """Restart a daemon."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    try:
        await daemon_service.restart_daemon(daemon_id)

        # Broadcast status update
        await websocket_manager.broadcast_daemon_update(daemon.to_dict())

        return {"message": f"Daemon {daemon.name} restarted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{daemon_id}", response_model=DaemonResponse)
async def update_daemon(
    daemon_id: str,
    update_request: DaemonUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Update daemon configuration."""
    try:
        daemon = await daemon_service.update_daemon_config(
            db=db,
            daemon_id=daemon_id,
            config=update_request.configuration,
            enabled=update_request.enabled,
            auto_start=update_request.auto_start,
        )

        # Broadcast update
        await websocket_manager.broadcast_daemon_update(daemon.to_dict())

        return daemon.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{daemon_id}/logs", response_model=List[DaemonLogResponse])
async def get_daemon_logs(
    daemon_id: str,
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[LogLevel] = None,
    since: Optional[datetime] = None,
):
    """Get daemon logs."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    logs = await daemon_service.get_daemon_logs(
        db=db, daemon_id=daemon_id, limit=limit, level=level, since=since
    )

    return [log.to_dict() for log in logs]


@router.get("/{daemon_id}/history", response_model=List[DaemonJobHistoryResponse])
async def get_daemon_job_history(
    daemon_id: str,
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(100, ge=1, le=1000),
    since: Optional[datetime] = None,
):
    """Get daemon job history."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    history = await daemon_service.get_daemon_job_history(
        db=db, daemon_id=daemon_id, limit=limit, since=since
    )

    return [h.to_dict() for h in history]


@router.get("/{daemon_id}/statistics")
async def get_daemon_statistics(
    daemon_id: str, db: AsyncSession = Depends(get_async_db)
):
    """Get comprehensive daemon statistics including errors, jobs, and health."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    try:
        stats = await daemon_observability_service.calculate_daemon_statistics(
            db, uuid.UUID(daemon_id)
        )
        return stats
    except Exception as e:
        logger.error(f"Failed to get daemon statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{daemon_id}/errors")
async def get_daemon_errors(
    daemon_id: str,
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(10, ge=1, le=100),
    unresolved_only: bool = Query(True),
):
    """Get daemon errors."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    errors = await daemon_observability_service.get_daemon_errors(
        db, uuid.UUID(daemon_id), limit=limit, unresolved_only=unresolved_only
    )
    return [error.to_dict() for error in errors]


@router.post("/{daemon_id}/errors/{error_id}/resolve")
async def resolve_daemon_error(
    daemon_id: str, error_id: str, db: AsyncSession = Depends(get_async_db)
):
    """Mark a daemon error as resolved."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    error = await daemon_observability_service.resolve_error(db, uuid.UUID(error_id))
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    return {"message": "Error resolved", "error": error.to_dict()}


@router.get("/{daemon_id}/activities")
async def get_daemon_activities(
    daemon_id: str,
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
):
    """Get recent daemon activities."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    activities = await daemon_observability_service.get_recent_activities(
        db, daemon_id=uuid.UUID(daemon_id), limit=limit, severity=severity
    )
    return [activity.to_dict() for activity in activities]


@router.get("/activities/all")
async def get_all_daemon_activities(
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(100, ge=1, le=500),
    severity: Optional[str] = Query(None),
):
    """Get recent activities from all daemons."""
    activities = await daemon_observability_service.get_recent_activities(
        db, daemon_id=None, limit=limit, severity=severity
    )

    # Add daemon name to each activity
    result = []
    for activity in activities:
        activity_dict = activity.to_dict()
        daemon = await daemon_service.get_daemon(db, str(activity.daemon_id))
        if daemon:
            activity_dict["daemon_name"] = daemon.name
        result.append(activity_dict)

    return result


@router.get("/{daemon_id}/metrics")
async def get_daemon_metrics(
    daemon_id: str,
    db: AsyncSession = Depends(get_async_db),
    metric_name: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get daemon performance metrics."""
    # Check if daemon exists
    daemon = await daemon_service.get_daemon(db, daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    metrics = await daemon_observability_service.get_daemon_metrics(
        db,
        uuid.UUID(daemon_id),
        metric_name=metric_name,
        since=since,
        limit=limit,
    )
    return [metric.to_dict() for metric in metrics]


@router.post("/{daemon_id}/test-broadcast")
async def test_daemon_broadcast(daemon_id: str):
    """Test endpoint to manually trigger a daemon log broadcast."""
    logger.info(f"Test broadcast endpoint called for daemon_id: {daemon_id}")

    test_log = {
        "id": str(uuid.uuid4()),
        "daemon_id": daemon_id,
        "level": "INFO",
        "message": "Test broadcast message",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"About to broadcast test log: {test_log}")
    await websocket_manager.broadcast_daemon_log(daemon_id=daemon_id, log=test_log)
    logger.info("Test broadcast complete")

    return {"message": "Test broadcast sent", "log": test_log}
