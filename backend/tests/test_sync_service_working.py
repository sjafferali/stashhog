"""Working tests for sync service that match actual implementation."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.models import Job, JobStatus, Scene
from app.services.sync.models import SyncResult, SyncStats, SyncStatus
from app.services.sync.strategies import SmartSyncStrategy
from app.services.sync.sync_service import SyncService


class TestSyncService:
    """Test sync service functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.query = Mock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()

        # Create a proper mock sync history instance
        from app.models.sync_history import SyncHistory

        mock_sync_history = Mock(spec=SyncHistory)
        mock_sync_history.id = 1
        mock_sync_history.completed_at = datetime.utcnow()
        mock_sync_history.status = "completed"
        mock_sync_history.items_synced = 0
        mock_sync_history.items_created = 0
        mock_sync_history.items_updated = 0
        mock_sync_history.items_failed = 0

        # Mock the execute method to return proper result object
        mock_result = Mock()
        # Make sure scalar_one returns the mock object, not a coroutine
        mock_result.scalar_one = lambda: mock_sync_history
        mock_result.scalar_one_or_none = lambda: mock_sync_history
        mock_result.scalars = lambda: Mock(all=lambda: [mock_sync_history])
        db.execute = AsyncMock(return_value=mock_result)

        # Mock flush to set ID on added objects
        def mock_flush_side_effect():
            # Set ID on any SyncHistory objects that were added
            if db.add.call_args and db.add.call_args[0]:
                obj = db.add.call_args[0][0]
                if (
                    hasattr(obj, "__class__")
                    and obj.__class__.__name__ == "SyncHistory"
                ):
                    obj.id = 1
            return None

        db.flush = AsyncMock(side_effect=mock_flush_side_effect)

        return db

    @pytest.fixture
    def mock_stash_service(self):
        """Create mock stash service."""
        mock = AsyncMock()
        # Default mock responses
        mock.get_stats = AsyncMock(
            return_value={
                "scene_count": 100,
                "performer_count": 50,
                "tag_count": 200,
                "studio_count": 10,
            }
        )
        mock.find_scenes = AsyncMock(return_value={"scenes": []})
        mock.find_performers = AsyncMock(return_value={"performers": []})
        mock.find_tags = AsyncMock(return_value={"tags": []})
        mock.find_studios = AsyncMock(return_value={"studios": []})
        return mock

    @pytest.fixture
    def sync_service(self, mock_stash_service, mock_db):
        """Create sync service instance."""
        service = SyncService(stash_service=mock_stash_service, db_session=mock_db)
        # Mock the handlers to avoid complex initialization
        service.scene_handler = Mock()
        service.entity_handler = Mock()
        return service

    def test_initialization(self, mock_stash_service, mock_db):
        """Test service initialization."""
        service = SyncService(stash_service=mock_stash_service, db_session=mock_db)

        assert service.stash_service == mock_stash_service
        assert service.db == mock_db
        assert hasattr(service, "scene_handler")
        assert hasattr(service, "entity_handler")
        assert hasattr(service, "conflict_resolver")
        assert isinstance(service.strategy, SmartSyncStrategy)

    @pytest.mark.asyncio
    async def test_sync_all(self, sync_service, mock_stash_service, mock_db):
        """Test full sync functionality."""
        # Mock _get_last_sync_time to avoid database queries
        sync_service._get_last_sync_time = AsyncMock(return_value=None)

        # Mock _update_job_status to avoid database queries and update the job object
        async def mock_update_job_status(job_id, status, message=None):
            if job_id == "test_job":
                mock_job.status = status

        sync_service._update_job_status = AsyncMock(side_effect=mock_update_job_status)
        # Mock _update_last_sync_time to avoid database queries
        sync_service._update_last_sync_time = AsyncMock(return_value=1)

        # Mock job in database
        mock_job = Mock(spec=Job)
        mock_job.job_metadata = {}  # Initialize metadata as dict
        mock_job.status = JobStatus.RUNNING
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        # Mock entity sync results
        sync_service.entity_handler.sync_performers = AsyncMock(
            return_value={"processed": 50, "created": 10, "updated": 40}
        )
        sync_service.entity_handler.sync_tags = AsyncMock(
            return_value={"processed": 200, "created": 50, "updated": 150}
        )
        sync_service.entity_handler.sync_studios = AsyncMock(
            return_value={"processed": 10, "created": 2, "updated": 8}
        )

        # Mock scene sync
        mock_stash_service.find_scenes = AsyncMock(
            return_value={
                "scenes": [
                    {"id": "1", "title": "Scene 1"},
                    {"id": "2", "title": "Scene 2"},
                ]
            }
        )

        # Mock get_scenes to return tuple format
        mock_stash_service.get_scenes = AsyncMock(
            side_effect=[
                ([{"id": "1", "title": "Scene 1"}, {"id": "2", "title": "Scene 2"}], 2),
                ([], 0),  # Empty batch to end loop
            ]
        )

        # Ensure get_stats returns proper values for full sync
        mock_stash_service.get_stats = AsyncMock(
            return_value={
                "scene_count": 2,
                "performer_count": 0,
                "tag_count": 0,
                "studio_count": 0,
            }
        )

        # Mock get_all_* methods for entity sync
        mock_stash_service.get_all_performers = AsyncMock(return_value=[])
        mock_stash_service.get_all_tags = AsyncMock(return_value=[])
        mock_stash_service.get_all_studios = AsyncMock(return_value=[])

        # Don't override the execute mock - it's already set up in the fixture
        # Just ensure scalar_one_or_none returns None for scene lookups
        mock_db.execute.return_value.scalar_one_or_none = Mock(return_value=None)

        # Mock scene handler
        sync_service.scene_handler.sync_scene = AsyncMock()

        # Mock strategy
        sync_service.strategy.should_sync = AsyncMock(return_value=True)

        # Run sync
        result = await sync_service.sync_all(job_id="test_job", cancellation_token=None)

        # Verify result
        assert isinstance(result, SyncResult)
        assert result.job_id == "test_job"
        assert result.status == SyncStatus.SUCCESS

        # Verify job status was updated
        assert mock_job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_sync_scenes(self, sync_service, mock_stash_service, mock_db):
        """Test scene sync functionality."""
        # Mock _get_last_sync_time to avoid database queries
        sync_service._get_last_sync_time = AsyncMock(return_value=None)
        # Mock _update_last_sync_time to avoid database queries
        sync_service._update_last_sync_time = AsyncMock(return_value=1)

        # Mock scene data
        mock_scenes = [
            {"id": "1", "title": "Scene 1", "path": "/path1.mp4"},
            {"id": "2", "title": "Scene 2", "path": "/path2.mp4"},
        ]

        # Mock find_scenes to return the expected format
        mock_stash_service.find_scenes = AsyncMock(
            side_effect=[
                {"scenes": mock_scenes},  # First call returns scenes
                {"scenes": []},  # Second call returns empty to end loop
            ]
        )

        # Mock get_scenes to return tuple format
        mock_stash_service.get_scenes = AsyncMock(
            side_effect=[
                (mock_scenes, len(mock_scenes)),  # First call returns scenes and count
                ([], 0),  # Second call returns empty to end loop
            ]
        )

        # Ensure get_stats returns proper values for full sync
        mock_stash_service.get_stats = AsyncMock(
            return_value={
                "scene_count": 2,
                "performer_count": 0,
                "tag_count": 0,
                "studio_count": 0,
            }
        )

        # Don't override the execute mock - it's already set up in the fixture
        # Just ensure scalar_one_or_none returns None for scene lookups
        mock_db.execute.return_value.scalar_one_or_none = Mock(return_value=None)

        # Mock scene handler
        sync_service.scene_handler.sync_scene = AsyncMock()

        # Mock strategy
        sync_service.strategy.should_sync = AsyncMock(return_value=True)

        # Run sync
        result = await sync_service.sync_scenes(job_id="test_job")

        # Verify result
        assert isinstance(result, SyncResult)
        assert result.stats.scenes_processed == 2
        assert result.status == SyncStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_sync_scene_by_id(self, sync_service, mock_stash_service, mock_db):
        """Test syncing a single scene by ID."""
        scene_id = "scene123"
        scene_data = {"id": scene_id, "title": "Test Scene", "path": "/test/scene.mp4"}

        # Mock stash service
        mock_stash_service.get_scene = AsyncMock(return_value=scene_data)

        # Don't override the execute mock - it's already set up in the fixture

        # Mock scene handler
        sync_service.scene_handler.sync_scene = AsyncMock()

        # Mock strategy
        sync_service.strategy.should_sync = AsyncMock(return_value=True)

        # Run sync
        result = await sync_service.sync_scene_by_id(scene_id)

        # Verify
        assert result.total_items == 1
        assert result.processed_items == 1
        assert result.stats.scenes_processed == 1
        assert result.status == SyncStatus.SUCCESS

        # Verify scene handler was called
        sync_service.scene_handler.sync_scene.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_performers(self, sync_service, mock_stash_service):
        """Test performer sync functionality."""
        # Mock get_all_performers to return transformed data
        mock_stash_service.get_all_performers = AsyncMock(
            return_value=[
                {"id": "p1", "name": "Performer 1"},
                {"id": "p2", "name": "Performer 2"},
            ]
        )

        # Mock entity handler
        sync_service.entity_handler.sync_performers = AsyncMock(
            return_value={"processed": 2, "created": 1, "updated": 1}
        )

        # Run sync
        result = await sync_service.sync_performers(job_id="test_job")

        # Verify
        assert result.processed_items == 2
        assert result.created_items == 1
        assert result.updated_items == 1
        assert result.stats.performers_processed == 2
        assert result.status == SyncStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_sync_tags(self, sync_service, mock_stash_service):
        """Test tag sync functionality."""
        # Mock get_all_tags to return transformed data
        mock_stash_service.get_all_tags = AsyncMock(
            return_value=[
                {"id": "t1", "name": "Tag 1"},
                {"id": "t2", "name": "Tag 2"},
            ]
        )

        # Mock entity handler
        sync_service.entity_handler.sync_tags = AsyncMock(
            return_value={"processed": 2, "created": 1, "updated": 1}
        )

        # Run sync
        result = await sync_service.sync_tags(job_id="test_job")

        # Verify
        assert result.processed_items == 2
        assert result.created_items == 1
        assert result.updated_items == 1
        assert result.stats.tags_processed == 2
        assert result.status == SyncStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_sync_studios(self, sync_service, mock_stash_service):
        """Test studio sync functionality."""
        # Mock get_all_studios to return transformed data
        mock_stash_service.get_all_studios = AsyncMock(
            return_value=[
                {"id": "s1", "name": "Studio 1"},
                {"id": "s2", "name": "Studio 2"},
            ]
        )

        # Mock entity handler
        sync_service.entity_handler.sync_studios = AsyncMock(
            return_value={"processed": 2, "created": 1, "updated": 1}
        )

        # Run sync
        result = await sync_service.sync_studios(job_id="test_job")

        # Verify
        assert result.processed_items == 2
        assert result.created_items == 1
        assert result.updated_items == 1
        assert result.stats.studios_processed == 2
        assert result.status == SyncStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_sync_with_progress_callback(self, sync_service, mock_stash_service):
        """Test sync with progress reporting."""
        # Mock _get_last_sync_time to avoid database queries
        sync_service._get_last_sync_time = AsyncMock(return_value=None)
        # Mock _update_last_sync_time to avoid database queries
        sync_service._update_last_sync_time = AsyncMock(return_value=1)

        progress_updates = []

        async def progress_callback(progress, message):
            progress_updates.append((progress, message))

        # Mock scene data
        mock_stash_service.find_scenes = AsyncMock(
            side_effect=[{"scenes": [{"id": "1", "title": "Scene 1"}]}, {"scenes": []}]
        )

        # Mock get_scenes to return tuple format
        mock_stash_service.get_scenes = AsyncMock(
            side_effect=[
                ([{"id": "1", "title": "Scene 1"}], 1),
                ([], 0),  # Empty batch to end loop
            ]
        )

        # Ensure get_stats returns proper values for full sync
        mock_stash_service.get_stats = AsyncMock(
            return_value={
                "scene_count": 1,
                "performer_count": 0,
                "tag_count": 0,
                "studio_count": 0,
            }
        )

        # Mock handlers
        sync_service.scene_handler.sync_scene = AsyncMock()
        sync_service.strategy.should_sync = AsyncMock(return_value=True)

        # Run sync
        await sync_service.sync_scenes(
            job_id="test_job", progress_callback=progress_callback
        )

        # Verify progress was reported
        assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_sync_error_handling(self, sync_service, mock_stash_service, mock_db):
        """Test error handling during sync."""
        # Configure the existing mock_stash_service methods
        mock_stash_service.get_all_performers.return_value = []
        mock_stash_service.get_all_tags.return_value = []
        mock_stash_service.get_all_studios.return_value = []

        # Configure scene sync to fail at get_scenes level
        mock_stash_service.get_scenes.side_effect = Exception("Network error")

        # Run sync and expect failure
        with pytest.raises(Exception) as exc_info:
            await sync_service.sync_scenes(job_id="test_job")

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sync_single_scene_with_existing(self, sync_service, mock_db):
        """Test syncing a scene that already exists."""
        scene_data = {
            "id": "123",
            "title": "Updated Title",
            "path": "/path/to/scene.mp4",
        }

        # Mock existing scene
        existing_scene = Mock(spec=Scene)
        existing_scene.id = "123"
        existing_scene.title = "Old Title"

        # Don't override the execute mock - it's already set up in the fixture
        # But we need to return the existing scene for lookups
        mock_db.execute.return_value.scalar_one_or_none = Mock(
            return_value=existing_scene
        )

        # Mock scene handler
        sync_service.scene_handler.sync_scene = AsyncMock(return_value=existing_scene)

        # Mock strategy
        sync_service.strategy.should_sync = AsyncMock(return_value=True)

        # Create result object
        result = SyncResult(job_id="test", started_at=datetime.utcnow())

        # Run sync
        await sync_service._sync_single_scene(scene_data, result)

        # Verify
        assert result.updated_items == 1
        assert result.stats.scenes_updated == 1
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_sync_single_scene_skip(self, sync_service, mock_db):
        """Test skipping a scene based on strategy."""
        scene_data = {"id": "123", "title": "Scene"}

        # Don't override the execute mock - it's already set up in the fixture

        # Mock strategy to skip
        sync_service.strategy.should_sync = AsyncMock(return_value=False)

        # Create result object
        result = SyncResult(job_id="test", started_at=datetime.utcnow())

        # Run sync
        await sync_service._sync_single_scene(scene_data, result)

        # Verify scene was skipped
        assert result.skipped_items == 1
        assert result.stats.scenes_skipped == 1
        assert not sync_service.scene_handler.sync_scene.called

    @pytest.mark.asyncio
    async def test_sync_entities_error_handling(self, sync_service, mock_stash_service):
        """Test error handling in entity sync."""
        # Mock _get_last_sync_time to avoid database queries
        sync_service._get_last_sync_time = AsyncMock(return_value=None)

        # Mock performer sync to fail
        mock_stash_service.get_all_performers = AsyncMock(
            side_effect=Exception("API Error")
        )
        # Mock other entity methods to succeed
        mock_stash_service.get_all_tags = AsyncMock(return_value=[])
        mock_stash_service.get_all_studios = AsyncMock(return_value=[])

        # Run entity sync
        results = await sync_service._sync_entities()

        # Verify error was captured
        assert "error" in results["performers"]
        assert "API Error" in results["performers"]["error"]

    def test_sync_stats_increments(self):
        """Test SyncStats increment methods."""
        stats = SyncStats()

        # Test scene increments
        stats.increment_processed("scenes")
        stats.increment_created("scenes")
        stats.increment_updated("scenes")
        stats.increment_skipped("scenes")
        stats.increment_failed("scenes")

        assert stats.scenes_processed == 1
        assert stats.scenes_created == 1
        assert stats.scenes_updated == 1
        assert stats.scenes_skipped == 1
        assert stats.scenes_failed == 1

        # Test performer increments
        stats.increment_processed("performers")
        stats.increment_created("performers")

        assert stats.performers_processed == 1
        assert stats.performers_created == 1

    def test_sync_result_completion(self):
        """Test SyncResult completion methods."""
        result = SyncResult(job_id="test", started_at=datetime.utcnow())

        # Test successful completion
        result.complete()
        assert result.status == SyncStatus.SUCCESS
        assert result.completed_at is not None

        # Test failed completion
        result2 = SyncResult(job_id="test2", started_at=datetime.utcnow())
        result2.complete(SyncStatus.FAILED)
        assert result2.status == SyncStatus.FAILED

    def test_sync_result_add_error(self):
        """Test adding errors to sync result."""
        result = SyncResult(job_id="test", started_at=datetime.utcnow())

        # Add an error
        result.add_error("scene", "123", "Failed to sync")

        assert len(result.errors) == 1
        assert result.errors[0].entity_type == "scene"
        assert result.errors[0].entity_id == "123"
        assert "Failed to sync" in result.errors[0].message
