import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.services.sync.models import SyncResult, SyncStatus
from app.services.sync.progress import BatchProgress, SyncProgress
from app.services.websocket_manager import WebSocketManager


@pytest.fixture
def websocket_manager():
    """Mock WebSocket manager"""
    manager = AsyncMock(spec=WebSocketManager)
    manager.broadcast_json = AsyncMock()
    return manager


@pytest.fixture
def sync_progress():
    """Create a SyncProgress instance"""
    return SyncProgress(job_id="test-job-123", total_items=100)


@pytest.fixture
def batch_progress():
    """Create a BatchProgress instance"""
    return BatchProgress(job_id="batch-job-123", batch_size=10)


class TestSyncProgress:
    """Test cases for SyncProgress class"""

    def test_initialization(self, sync_progress):
        """Test SyncProgress initialization"""
        assert sync_progress.job_id == "test-job-123"
        assert sync_progress.total_items == 100
        assert sync_progress.processed_items == 0
        assert sync_progress.errors == []
        assert isinstance(sync_progress.start_time, datetime)
        assert sync_progress.update_interval == 1.0
        assert sync_progress._websocket_manager is None

    def test_set_websocket_manager(self, sync_progress, websocket_manager):
        """Test setting WebSocket manager"""
        sync_progress.set_websocket_manager(websocket_manager)
        assert sync_progress._websocket_manager == websocket_manager

    @pytest.mark.asyncio
    async def test_update_basic(self, sync_progress):
        """Test basic progress update without WebSocket"""
        await sync_progress.update(50)
        assert sync_progress.processed_items == 50
        assert len(sync_progress.errors) == 0

    @pytest.mark.asyncio
    async def test_update_with_error(self, sync_progress):
        """Test update with error"""
        await sync_progress.update(10, error="Test error")
        assert sync_progress.processed_items == 10
        assert len(sync_progress.errors) == 1
        assert sync_progress.errors[0].error_message == "Test error"
        assert sync_progress.errors[0].entity_type == "unknown"
        assert sync_progress.errors[0].entity_id == "unknown"

    @pytest.mark.asyncio
    async def test_update_throttling(self, sync_progress, websocket_manager):
        """Test update throttling"""
        sync_progress.set_websocket_manager(websocket_manager)
        sync_progress.update_interval = 0.1  # Reduce interval for faster testing

        # First update should go through
        await sync_progress.update(10, force_update=True)
        assert websocket_manager.broadcast_json.call_count == 1

        # Immediate second update should be throttled
        await sync_progress.update(20)
        assert websocket_manager.broadcast_json.call_count == 1

        # Wait for throttle interval to pass
        await asyncio.sleep(0.15)

        # Now update should go through
        await sync_progress.update(30)
        assert websocket_manager.broadcast_json.call_count == 2

        # Force update should bypass throttling
        await sync_progress.update(40, force_update=True)
        assert websocket_manager.broadcast_json.call_count == 3

    @pytest.mark.asyncio
    async def test_update_with_details(self, sync_progress, websocket_manager):
        """Test detailed update"""
        sync_progress.set_websocket_manager(websocket_manager)

        await sync_progress.update_with_details(
            processed=25, entity_type="scene", entity_id="scene-123", action="created"
        )

        assert sync_progress.processed_items == 25
        assert websocket_manager.broadcast_json.called

        # Check the broadcast data
        call_args = websocket_manager.broadcast_json.call_args[0][0]
        assert call_args["type"] == "sync_detail"
        assert call_args["job_id"] == "test-job-123"
        assert call_args["detail"]["entity_type"] == "scene"
        assert call_args["detail"]["entity_id"] == "scene-123"
        assert call_args["detail"]["action"] == "created"

    @pytest.mark.asyncio
    async def test_update_with_details_and_error(
        self, sync_progress, websocket_manager
    ):
        """Test detailed update with error"""
        sync_progress.set_websocket_manager(websocket_manager)

        await sync_progress.update_with_details(
            processed=30,
            entity_type="performer",
            entity_id="performer-456",
            action="failed",
            error="Validation failed",
        )

        assert sync_progress.processed_items == 30
        assert len(sync_progress.errors) == 1
        assert sync_progress.errors[0].entity_type == "performer"
        assert sync_progress.errors[0].entity_id == "performer-456"
        assert sync_progress.errors[0].error_message == "Validation failed"

    @pytest.mark.asyncio
    async def test_complete(self, sync_progress, websocket_manager):
        """Test completion notification"""
        sync_progress.set_websocket_manager(websocket_manager)
        sync_progress.processed_items = 95

        # Create a result
        result = SyncResult(
            job_id="test-job-123",
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
            status=SyncStatus.SUCCESS,
            total_items=100,
            processed_items=95,
            created_items=20,
            updated_items=70,
            skipped_items=5,
            failed_items=0,
        )

        await sync_progress.complete(result)

        assert websocket_manager.broadcast_json.called
        call_args = websocket_manager.broadcast_json.call_args[0][0]
        assert call_args["type"] == "sync_complete"
        assert call_args["job_id"] == "test-job-123"
        assert call_args["result"]["status"] == "success"
        assert call_args["result"]["total_items"] == 100
        assert call_args["result"]["processed_items"] == 95

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, sync_progress, websocket_manager):
        """Test WebSocket error handling"""
        sync_progress.set_websocket_manager(websocket_manager)
        websocket_manager.broadcast_json.side_effect = Exception("WebSocket error")

        # Should not raise exception
        await sync_progress.update(50, force_update=True)
        assert sync_progress.processed_items == 50

    def test_calculate_percentage(self, sync_progress):
        """Test percentage calculation"""
        assert sync_progress._calculate_percentage() == 0.0

        sync_progress.processed_items = 50
        assert sync_progress._calculate_percentage() == 50.0

        sync_progress.processed_items = 100
        assert sync_progress._calculate_percentage() == 100.0

        # Test edge case: more processed than total
        sync_progress.processed_items = 150
        assert sync_progress._calculate_percentage() == 100.0

        # Test edge case: zero total items
        sync_progress.total_items = 0
        assert sync_progress._calculate_percentage() == 100.0

    def test_calculate_elapsed_seconds(self, sync_progress):
        """Test elapsed time calculation"""
        # Mock start time to be 10 seconds ago
        sync_progress.start_time = datetime.utcnow() - timedelta(seconds=10)

        elapsed = sync_progress._calculate_elapsed_seconds()
        assert 9.9 <= elapsed <= 10.1  # Allow small variance

    def test_estimate_remaining_seconds(self, sync_progress):
        """Test remaining time estimation"""
        # No items processed yet
        assert sync_progress._estimate_remaining_seconds() is None

        # Mock progress: 25 items in 10 seconds
        sync_progress.start_time = datetime.utcnow() - timedelta(seconds=10)
        sync_progress.processed_items = 25

        remaining = sync_progress._estimate_remaining_seconds()
        # Rate: 2.5 items/sec, 75 items remaining = 30 seconds
        assert remaining is not None
        assert 29 <= remaining <= 31  # Allow small variance

        # All items processed
        sync_progress.processed_items = 100
        remaining = sync_progress._estimate_remaining_seconds()
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_progress_update_data_format(self, sync_progress, websocket_manager):
        """Test the format of progress update data"""
        sync_progress.set_websocket_manager(websocket_manager)
        sync_progress.processed_items = 40

        await sync_progress.update(40, force_update=True)

        call_args = websocket_manager.broadcast_json.call_args[0][0]
        assert "type" in call_args
        assert "job_id" in call_args
        assert "progress" in call_args

        progress = call_args["progress"]
        assert progress["processed"] == 40
        assert progress["total"] == 100
        assert progress["percentage"] == 40.0
        assert "elapsed_seconds" in progress
        assert "estimated_remaining_seconds" in progress
        assert progress["errors"] == 0


class TestBatchProgress:
    """Test cases for BatchProgress class"""

    def test_initialization(self, batch_progress):
        """Test BatchProgress initialization"""
        assert batch_progress.job_id == "batch-job-123"
        assert batch_progress.batch_size == 10
        assert batch_progress.current_batch == 0
        assert batch_progress.items_in_batch == 0
        assert batch_progress.total_processed == 0

    def test_start_batch(self, batch_progress):
        """Test starting a new batch"""
        batch_progress.start_batch(3)
        assert batch_progress.current_batch == 3
        assert batch_progress.items_in_batch == 0

    def test_increment(self, batch_progress):
        """Test incrementing progress"""
        batch_progress.start_batch(1)

        batch_progress.increment()
        assert batch_progress.items_in_batch == 1
        assert batch_progress.total_processed == 1

        batch_progress.increment()
        assert batch_progress.items_in_batch == 2
        assert batch_progress.total_processed == 2

    def test_complete_batch(self, batch_progress):
        """Test batch completion logging"""
        batch_progress.start_batch(2)
        batch_progress.increment()
        batch_progress.increment()
        batch_progress.increment()

        # Verify state before completion
        assert batch_progress.current_batch == 2
        assert batch_progress.items_in_batch == 3
        assert batch_progress.total_processed == 3

        # complete_batch just logs, doesn't change state
        batch_progress.complete_batch()

        # Verify state after completion
        assert batch_progress.current_batch == 2
        assert batch_progress.items_in_batch == 3
        assert batch_progress.total_processed == 3

    def test_multiple_batches(self, batch_progress):
        """Test processing multiple batches"""
        # Batch 1
        batch_progress.start_batch(1)
        for _ in range(5):
            batch_progress.increment()
        batch_progress.complete_batch()

        # Batch 2
        batch_progress.start_batch(2)
        for _ in range(3):
            batch_progress.increment()
        batch_progress.complete_batch()

        assert batch_progress.total_processed == 8
        assert batch_progress.current_batch == 2
        assert batch_progress.items_in_batch == 3


class TestProgressIntegration:
    """Integration tests for progress tracking"""

    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, websocket_manager):
        """Test complete sync workflow with progress tracking"""
        progress = SyncProgress("integration-job", total_items=50)
        progress.set_websocket_manager(websocket_manager)

        # Simulate processing items
        for i in range(1, 51):
            if i % 10 == 0:
                # Every 10th item has an error
                await progress.update_with_details(
                    processed=i,
                    entity_type="scene",
                    entity_id=f"scene-{i}",
                    action="failed",
                    error=f"Processing error for item {i}",
                )
            else:
                await progress.update_with_details(
                    processed=i,
                    entity_type="scene",
                    entity_id=f"scene-{i}",
                    action="updated",
                )

            # Add delay to test throttling
            await asyncio.sleep(0.01)

        # Complete the sync
        result = SyncResult(
            job_id="integration-job",
            started_at=progress.start_time,
            completed_at=datetime.utcnow(),
            total_items=50,
            processed_items=50,
            created_items=0,
            updated_items=45,
            failed_items=5,
            errors=progress.errors,
        )

        await progress.complete(result)

        # Verify errors were tracked
        assert len(progress.errors) == 5
        assert all(e.entity_type == "scene" for e in progress.errors)

        # Verify WebSocket was called
        assert websocket_manager.broadcast_json.called

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, websocket_manager):
        """Test concurrent progress updates"""
        progress = SyncProgress("concurrent-job", total_items=1000)
        progress.set_websocket_manager(websocket_manager)
        progress.update_interval = 0.01  # Very short interval for testing

        # Simulate concurrent updates
        async def update_progress(start, end):
            for i in range(start, end):
                await progress.update(i)
                await asyncio.sleep(0.002)

        # Run multiple update tasks concurrently
        tasks = [
            update_progress(0, 250),
            update_progress(250, 500),
            update_progress(500, 750),
            update_progress(750, 1000),
        ]

        await asyncio.gather(*tasks)

        # Verify final state
        assert progress.processed_items >= 750  # At least some updates processed
        assert websocket_manager.broadcast_json.called


class TestRealTimeProgressUpdates:
    """Test cases for real-time progress update functionality"""

    @pytest.mark.asyncio
    async def test_websocket_message_formats(self, websocket_manager):
        """Test WebSocket message formats for different update types"""
        progress = SyncProgress("format-test-job", total_items=10)
        progress.set_websocket_manager(websocket_manager)

        # Test progress update format
        await progress.update(5, force_update=True)

        call_args = websocket_manager.broadcast_json.call_args_list[-1][0][0]
        assert call_args["type"] == "sync_progress"
        assert call_args["job_id"] == "format-test-job"
        assert "progress" in call_args
        assert call_args["progress"]["processed"] == 5
        assert call_args["progress"]["total"] == 10
        assert call_args["progress"]["percentage"] == 50.0

        # Test detailed update format
        await progress.update_with_details(
            processed=6, entity_type="performer", entity_id="perf-123", action="created"
        )

        call_args = websocket_manager.broadcast_json.call_args_list[-1][0][0]
        assert call_args["type"] == "sync_detail"
        assert call_args["detail"]["entity_type"] == "performer"
        assert call_args["detail"]["entity_id"] == "perf-123"
        assert call_args["detail"]["action"] == "created"
        assert "timestamp" in call_args["detail"]

        # Test completion format
        result = SyncResult(
            job_id="format-test-job",
            started_at=progress.start_time,
            completed_at=datetime.utcnow(),
            status=SyncStatus.SUCCESS,
            total_items=10,
            processed_items=10,
            created_items=3,
            updated_items=7,
        )

        await progress.complete(result)

        call_args = websocket_manager.broadcast_json.call_args_list[-1][0][0]
        assert call_args["type"] == "sync_complete"
        assert call_args["result"]["status"] == "success"
        assert call_args["result"]["created_items"] == 3
        assert call_args["result"]["updated_items"] == 7

    @pytest.mark.asyncio
    async def test_error_tracking_in_realtime(self, websocket_manager):
        """Test real-time error tracking and reporting"""
        progress = SyncProgress("error-test-job", total_items=20)
        progress.set_websocket_manager(websocket_manager)

        # Add multiple errors
        errors = [
            ("scene", "scene-1", "Database constraint violation"),
            ("tag", "tag-5", "Invalid tag format"),
            ("performer", "perf-10", "External API error"),
        ]

        for i, (entity_type, entity_id, error_msg) in enumerate(errors):
            await progress.update_with_details(
                processed=i + 1,
                entity_type=entity_type,
                entity_id=entity_id,
                action="failed",
                error=error_msg,
            )

        # Complete with errors
        result = SyncResult(
            job_id="error-test-job",
            started_at=progress.start_time,
            completed_at=datetime.utcnow(),
            status=SyncStatus.PARTIAL,
            total_items=20,
            processed_items=3,
            failed_items=3,
            errors=progress.errors,
        )

        await progress.complete(result)

        # Verify error reporting in completion message
        call_args = websocket_manager.broadcast_json.call_args_list[-1][0][0]
        assert call_args["result"]["status"] == "partial"
        assert call_args["result"]["failed_items"] == 3
        assert len(call_args["result"]["errors"]) == 3

        # Verify error details
        reported_errors = call_args["result"]["errors"]
        assert any(e["entity_type"] == "scene" for e in reported_errors)
        assert any(e["error"] == "Invalid tag format" for e in reported_errors)

    @pytest.mark.asyncio
    async def test_progress_time_estimation(self, websocket_manager):
        """Test progress time estimation accuracy"""
        progress = SyncProgress("estimation-job", total_items=100)
        progress.set_websocket_manager(websocket_manager)

        # Mock start time to control timing
        start_time = datetime.utcnow() - timedelta(seconds=10)
        progress.start_time = start_time

        # Process 25 items (25% in 10 seconds)
        await progress.update(25, force_update=True)

        # Check time calculations
        elapsed = progress._calculate_elapsed_seconds()
        assert 9.5 <= elapsed <= 10.5

        remaining = progress._estimate_remaining_seconds()
        assert remaining is not None
        # 25 items in 10 seconds = 2.5 items/sec
        # 75 items remaining / 2.5 = 30 seconds
        assert 28 <= remaining <= 32

        # Verify estimates in WebSocket message
        call_args = websocket_manager.broadcast_json.call_args_list[-1][0][0]
        assert 9.5 <= call_args["progress"]["elapsed_seconds"] <= 10.5
        assert 28 <= call_args["progress"]["estimated_remaining_seconds"] <= 32

    @pytest.mark.asyncio
    async def test_batch_progress_with_websocket(self, websocket_manager):
        """Test batch progress tracking with WebSocket updates"""
        sync_progress = SyncProgress("batch-sync-job", total_items=30)
        sync_progress.set_websocket_manager(websocket_manager)
        batch_progress = BatchProgress("batch-sync-job", batch_size=10)

        # Process 3 batches
        for batch_num in range(3):
            batch_progress.start_batch(batch_num + 1)

            for i in range(10):
                batch_progress.increment()
                await sync_progress.update(
                    batch_progress.total_processed,
                    force_update=(i == 9),  # Force update at end of batch
                )

            batch_progress.complete_batch()

        # Verify progress tracking
        assert batch_progress.total_processed == 30
        assert sync_progress.processed_items == 30
        assert websocket_manager.broadcast_json.call_count >= 3

    @pytest.mark.asyncio
    async def test_websocket_reconnection_handling(self, websocket_manager):
        """Test handling of WebSocket disconnection/reconnection"""
        progress = SyncProgress("reconnect-job", total_items=10)
        progress.set_websocket_manager(websocket_manager)

        # Simulate WebSocket failure then recovery
        websocket_manager.broadcast_json.side_effect = [
            Exception("Connection lost"),
            None,  # Success after reconnection
            None,  # Success
        ]

        # Updates should not crash even with WebSocket errors
        await progress.update(3, force_update=True)  # Fails
        await progress.update(6, force_update=True)  # Succeeds
        await progress.update(10, force_update=True)  # Succeeds

        assert progress.processed_items == 10
        assert websocket_manager.broadcast_json.call_count == 3

    @pytest.mark.asyncio
    async def test_large_scale_progress_tracking(self, websocket_manager):
        """Test progress tracking with large number of items"""
        progress = SyncProgress("large-job", total_items=10000)
        progress.set_websocket_manager(websocket_manager)
        progress.update_interval = 1.0  # Update every second

        # Simulate rapid processing
        update_count = 0
        for i in range(100, 10001, 100):
            await progress.update(i)
            if websocket_manager.broadcast_json.called:
                update_count = websocket_manager.broadcast_json.call_count
            await asyncio.sleep(0.01)

        # Should have throttled updates appropriately
        assert update_count < 100  # Much less than 100 updates
        assert progress.processed_items == 10000

        # Final percentage should be 100%
        assert progress._calculate_percentage() == 100.0

    @pytest.mark.asyncio
    async def test_progress_state_consistency(self, websocket_manager):
        """Test progress state consistency under various conditions"""
        progress = SyncProgress("consistency-job", total_items=50)
        progress.set_websocket_manager(websocket_manager)

        # Test zero progress
        assert progress._calculate_percentage() == 0.0
        assert progress._estimate_remaining_seconds() is None

        # Test over-progress (more processed than total)
        progress.processed_items = 60
        assert progress._calculate_percentage() == 100.0

        # Test with zero total items
        progress2 = SyncProgress("empty-job", total_items=0)
        assert progress2._calculate_percentage() == 100.0
        assert progress2._estimate_remaining_seconds() is None
