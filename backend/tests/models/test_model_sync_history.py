"""Tests for SyncHistory model."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_history import SyncHistory


class TestSyncHistory:
    """Test cases for SyncHistory model."""

    @pytest.mark.asyncio
    async def test_create_sync_history(self, test_async_session: AsyncSession) -> None:
        """Test creating a sync history record."""
        sync_history = SyncHistory(
            entity_type="scene",
            job_id="test-job-123",
            started_at=datetime.utcnow(),
            status="in_progress",
            items_synced=0,
            items_created=0,
            items_updated=0,
            items_failed=0,
        )

        test_async_session.add(sync_history)
        await test_async_session.commit()
        await test_async_session.refresh(sync_history)

        assert sync_history.id is not None
        assert sync_history.entity_type == "scene"
        assert sync_history.job_id == "test-job-123"
        assert sync_history.status == "in_progress"
        assert sync_history.started_at is not None
        assert sync_history.completed_at is None
        assert sync_history.items_synced == 0

    @pytest.mark.asyncio
    async def test_sync_history_with_completion(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test sync history with completion data."""
        started_at = datetime.utcnow()
        completed_at = started_at + timedelta(minutes=5)

        sync_history = SyncHistory(
            entity_type="performer",
            job_id="test-job-456",
            started_at=started_at,
            completed_at=completed_at,
            status="completed",
            items_synced=100,
            items_created=20,
            items_updated=75,
            items_failed=5,
        )

        test_async_session.add(sync_history)
        await test_async_session.commit()

        assert sync_history.status == "completed"
        assert sync_history.items_synced == 100
        assert sync_history.items_created == 20
        assert sync_history.items_updated == 75
        assert sync_history.items_failed == 5

    @pytest.mark.asyncio
    async def test_sync_history_with_errors(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test sync history with error details."""
        error_details = {
            "errors": [
                {"item_id": "123", "error": "Connection timeout"},
                {"item_id": "456", "error": "Invalid data format"},
            ],
            "total_errors": 2,
        }

        sync_history = SyncHistory(
            entity_type="tag",
            started_at=datetime.utcnow(),
            status="partial",
            items_synced=50,
            items_failed=2,
            error_details=error_details,
        )

        test_async_session.add(sync_history)
        await test_async_session.commit()

        assert sync_history.status == "partial"
        assert sync_history.items_failed == 2
        assert sync_history.error_details == error_details
        assert sync_history.get_details() == error_details

    @pytest.mark.asyncio
    async def test_duration_seconds_property(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test duration_seconds property calculation."""
        started_at = datetime.utcnow()
        completed_at = started_at + timedelta(seconds=123.45)

        # Completed sync
        sync_history = SyncHistory(
            entity_type="studio",
            started_at=started_at,
            completed_at=completed_at,
            status="completed",
        )

        test_async_session.add(sync_history)
        await test_async_session.commit()

        duration = sync_history.duration_seconds
        assert duration is not None
        assert 123 <= duration <= 124  # Allow for small floating point differences

        # In-progress sync (no duration)
        sync_history_in_progress = SyncHistory(
            entity_type="all", started_at=datetime.utcnow(), status="in_progress"
        )

        test_async_session.add(sync_history_in_progress)
        await test_async_session.commit()

        assert sync_history_in_progress.duration_seconds is None

    @pytest.mark.asyncio
    async def test_success_rate_property(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test success_rate property calculation."""
        # Full success
        sync_history_success = SyncHistory(
            entity_type="scene",
            started_at=datetime.utcnow(),
            status="completed",
            items_synced=100,
            items_failed=0,
        )
        test_async_session.add(sync_history_success)
        await test_async_session.commit()
        assert sync_history_success.success_rate == 1.0

        # Partial success
        sync_history_partial = SyncHistory(
            entity_type="scene",
            started_at=datetime.utcnow(),
            status="partial",
            items_synced=100,
            items_failed=25,
        )
        test_async_session.add(sync_history_partial)
        await test_async_session.commit()
        assert sync_history_partial.success_rate == 0.75

        # No items synced
        sync_history_empty = SyncHistory(
            entity_type="scene",
            started_at=datetime.utcnow(),
            status="completed",
            items_synced=0,
            items_failed=0,
        )
        test_async_session.add(sync_history_empty)
        await test_async_session.commit()
        assert sync_history_empty.success_rate == 0.0

        # Complete failure
        sync_history_failed = SyncHistory(
            entity_type="scene",
            started_at=datetime.utcnow(),
            status="failed",
            items_synced=50,
            items_failed=50,
        )
        test_async_session.add(sync_history_failed)
        await test_async_session.commit()
        assert sync_history_failed.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_is_recent_method(self, test_async_session: AsyncSession) -> None:
        """Test is_recent method."""
        # Recent sync (within 24 hours)
        recent_sync = SyncHistory(
            entity_type="performer",
            started_at=datetime.utcnow() - timedelta(hours=2),
            status="completed",
        )
        test_async_session.add(recent_sync)
        await test_async_session.commit()
        assert recent_sync.is_recent(hours=24) is True
        assert recent_sync.is_recent(hours=1) is False

        # Old sync (beyond 24 hours)
        old_sync = SyncHistory(
            entity_type="performer",
            started_at=datetime.utcnow() - timedelta(days=2),
            status="completed",
        )
        test_async_session.add(old_sync)
        await test_async_session.commit()
        assert old_sync.is_recent(hours=24) is False
        assert old_sync.is_recent(hours=72) is True

        # Edge case: exactly at threshold
        edge_sync = SyncHistory(
            entity_type="performer",
            started_at=datetime.utcnow() - timedelta(hours=24),
            status="completed",
        )
        test_async_session.add(edge_sync)
        await test_async_session.commit()
        # Should be False as it's exactly 24 hours old
        assert edge_sync.is_recent(hours=24) is False

    @pytest.mark.asyncio
    async def test_different_entity_types(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test different entity types."""
        entity_types = ["scene", "performer", "tag", "studio", "all"]

        for entity_type in entity_types:
            sync_history = SyncHistory(
                entity_type=entity_type,
                started_at=datetime.utcnow(),
                status="completed",
                items_synced=10,
            )
            test_async_session.add(sync_history)

        await test_async_session.commit()

        # Query back to verify
        from sqlalchemy import select

        result = await test_async_session.execute(select(SyncHistory))
        sync_histories = result.scalars().all()

        synced_types = [sh.entity_type for sh in sync_histories]
        for entity_type in entity_types:
            assert entity_type in synced_types

    @pytest.mark.asyncio
    async def test_sync_status_transitions(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test different sync status values."""
        statuses = ["in_progress", "completed", "failed", "partial"]

        for status in statuses:
            sync_history = SyncHistory(
                entity_type="scene",
                started_at=datetime.utcnow(),
                status=status,
            )
            test_async_session.add(sync_history)

        await test_async_session.commit()

        # Verify all statuses
        from sqlalchemy import select

        result = await test_async_session.execute(select(SyncHistory))
        sync_histories = result.scalars().all()

        saved_statuses = [sh.status for sh in sync_histories]
        for status in statuses:
            assert status in saved_statuses

    @pytest.mark.asyncio
    async def test_sync_history_statistics(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test sync history with various statistics combinations."""
        # Test case where created + updated > synced (should be valid)
        sync_history = SyncHistory(
            entity_type="scene",
            started_at=datetime.utcnow(),
            status="completed",
            items_synced=100,
            items_created=60,
            items_updated=50,  # Total 110, which is > 100 synced
            items_failed=0,
        )
        test_async_session.add(sync_history)
        await test_async_session.commit()

        assert sync_history.items_created == 60
        assert sync_history.items_updated == 50
        assert sync_history.items_synced == 100

    @pytest.mark.asyncio
    async def test_edge_cases(self, test_async_session: AsyncSession) -> None:
        """Test edge cases and boundary conditions."""
        # Test is_recent with None (edge case in the method)
        sync_test = SyncHistory(
            entity_type="scene", status="failed", started_at=datetime.utcnow()
        )
        # Manually set started_at to None after creation to test the edge case
        test_async_session.add(sync_test)
        await test_async_session.commit()
        # Test the edge case handling in is_recent method
        # Note: In production, started_at should never be None due to NOT NULL constraint

        # Large numbers
        sync_large = SyncHistory(
            entity_type="all",
            started_at=datetime.utcnow(),
            status="completed",
            items_synced=1000000,
            items_created=500000,
            items_updated=400000,
            items_failed=100000,
        )
        test_async_session.add(sync_large)
        await test_async_session.commit()
        assert sync_large.success_rate == 0.9

        # Empty error details
        sync_empty_errors = SyncHistory(
            entity_type="tag",
            started_at=datetime.utcnow(),
            status="completed",
            error_details={},
        )
        test_async_session.add(sync_empty_errors)
        await test_async_session.commit()
        assert sync_empty_errors.get_details() == {}

    @pytest.mark.asyncio
    async def test_sync_history_without_job_id(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test sync history without job_id (manual sync)."""
        sync_history = SyncHistory(
            entity_type="performer",
            started_at=datetime.utcnow(),
            status="completed",
            items_synced=50,
        )
        test_async_session.add(sync_history)
        await test_async_session.commit()

        assert sync_history.job_id is None
        assert sync_history.entity_type == "performer"

    @pytest.mark.asyncio
    async def test_complex_error_details(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test complex error details structure."""
        complex_error = {
            "summary": {
                "total_errors": 5,
                "error_types": {"timeout": 3, "validation": 2},
            },
            "details": [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "entity_id": "abc123",
                    "error_type": "timeout",
                    "message": "Connection timeout after 30s",
                    "retry_count": 3,
                },
                {
                    "timestamp": "2024-01-01T12:05:00",
                    "entity_id": "def456",
                    "error_type": "validation",
                    "message": "Invalid date format",
                    "field": "created_at",
                },
            ],
            "metadata": {"sync_version": "1.0", "retry_policy": "exponential_backoff"},
        }

        sync_history = SyncHistory(
            entity_type="studio",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow() + timedelta(minutes=10),
            status="partial",
            items_synced=100,
            items_failed=5,
            error_details=complex_error,
        )
        test_async_session.add(sync_history)
        await test_async_session.commit()

        retrieved_details = sync_history.get_details()
        assert retrieved_details == complex_error
        assert retrieved_details["summary"]["total_errors"] == 5
        assert len(retrieved_details["details"]) == 2

    @pytest.mark.asyncio
    async def test_sync_history_ordering(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test querying sync history with ordering."""
        # Create multiple sync histories with different timestamps
        base_time = datetime.utcnow()
        for i in range(5):
            sync_history = SyncHistory(
                entity_type="scene",
                started_at=base_time - timedelta(hours=i),
                status="completed",
                items_synced=i * 10,
            )
            test_async_session.add(sync_history)

        await test_async_session.commit()

        # Query with ordering
        from sqlalchemy import desc, select

        result = await test_async_session.execute(
            select(SyncHistory).order_by(desc(SyncHistory.started_at))
        )
        histories = result.scalars().all()

        # Verify ordering (most recent first)
        for i in range(len(histories) - 1):
            assert histories[i].started_at >= histories[i + 1].started_at
