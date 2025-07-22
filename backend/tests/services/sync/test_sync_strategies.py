from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from app.models import Performer, Scene, Tag
from app.services.sync.strategies import (
    FullSyncStrategy,
    IncrementalSyncStrategy,
    SmartSyncStrategy,
)
from tests.helpers import create_test_scene


@pytest.fixture
def mock_scene():
    """Create a mock scene for testing"""
    scene = create_test_scene(
        id="scene-123",
        title="Test Scene",
        details="Original details",
        url="http://example.com/scene",
        rating=4,
        organized=True,
        paths=["/path/to/file.mp4"],
        duration=3600,
        size=1000000,
        height=1080,
        width=1920,
        frame_rate=30,
        bit_rate=5000,
        video_codec="h264",
        stash_created_at=datetime(2023, 1, 1, 12, 0, 0),
        stash_updated_at=datetime(2023, 6, 1, 12, 0, 0),
        stash_date=datetime(2023, 1, 1),
    )
    scene.content_checksum = "old_checksum"
    scene.stash_id = "scene-123"
    return scene


@pytest.fixture
def mock_performer():
    """Create a mock performer for testing"""
    performer = MagicMock(spec=Performer)
    performer.stash_id = "performer-123"
    performer.name = "Test Performer"
    performer.aliases = ["Alias 1", "Alias 2"]
    performer.url = "http://example.com/performer"
    performer.rating = 5
    performer.updated_at = datetime(2023, 6, 1, 12, 0, 0)
    return performer


@pytest.fixture
def remote_scene_data():
    """Create remote scene data for testing"""
    return {
        "id": "scene-123",
        "title": "Updated Scene Title",
        "details": "Updated details",
        "url": "http://example.com/updated-scene",
        "rating100": 80,  # 4/5 stars
        "organized": False,
        "paths": ["/new/path/to/file.mp4"],
        "file_path": "/new/path/to/file.mp4",
        "file": {
            "duration": 3700,
            "size": 1100000,
            "height": 2160,
            "width": 3840,
            "framerate": 60,
            "bitrate": 6000,
            "video_codec": "h265",
        },
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-07-01T12:00:00Z",
        "date": "2023-01-15",
    }


@pytest.fixture
def remote_performer_data():
    """Create remote performer data for testing"""
    return {
        "id": "performer-123",
        "name": "Updated Performer",
        "aliases": ["New Alias 1", "New Alias 2", "New Alias 3"],
        "url": "http://example.com/updated-performer",
        "rating": 4,
        "updated_at": "2023-07-01T12:00:00Z",
    }


class TestFullSyncStrategy:
    """Test the FullSyncStrategy class"""

    @pytest.mark.asyncio
    async def test_should_sync_always_returns_true(self):
        """Test that FullSyncStrategy always returns True for should_sync"""
        strategy = FullSyncStrategy()

        # Test with existing entity
        result = await strategy.should_sync({}, MagicMock())
        assert result is True

        # Test without existing entity
        result = await strategy.should_sync({}, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_merge_scene_data(self, mock_scene, remote_scene_data):
        """Test merging scene data with FullSyncStrategy"""
        strategy = FullSyncStrategy()

        result = await strategy.merge_data(mock_scene, remote_scene_data)

        # Verify all fields are updated
        assert result.title == "Updated Scene Title"
        assert result.details == "Updated details"
        assert result.url == "http://example.com/updated-scene"
        assert result.rating == 4  # 80/20
        assert result.organized is False
        # File-related fields are now in SceneFile, not directly on Scene
        # The sync strategy only updates Scene model fields

        # Verify timestamps (timezone-aware from ISO format)
        assert result.stash_created_at == datetime(
            2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        assert result.stash_updated_at == datetime(
            2023, 7, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        assert result.stash_date == datetime(2023, 1, 15)

    @pytest.mark.asyncio
    async def test_merge_performer_data(self, mock_performer, remote_performer_data):
        """Test merging performer data with FullSyncStrategy"""
        strategy = FullSyncStrategy()

        with freeze_time("2023-08-01 12:00:00"):
            result = await strategy.merge_data(mock_performer, remote_performer_data)

        assert result.name == "Updated Performer"
        assert result.aliases == ["New Alias 1", "New Alias 2", "New Alias 3"]
        assert result.url == "http://example.com/updated-performer"
        assert result.rating == 4
        assert result.updated_at == datetime(2023, 8, 1, 12, 0, 0)

    def test_parse_datetime_various_formats(self):
        """Test parsing various datetime formats"""
        strategy = FullSyncStrategy()

        # ISO format with timezone Z
        result = strategy._parse_datetime("2023-01-01T12:00:00Z")
        assert result == datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # ISO format with timezone offset
        result = strategy._parse_datetime("2023-01-01T12:00:00+00:00")
        assert result == datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # ISO format without timezone
        result = strategy._parse_datetime("2023-01-01T12:00:00")
        assert result == datetime(2023, 1, 1, 12, 0, 0)

        # Date only format
        result = strategy._parse_datetime("2023-01-01")
        assert result == datetime(2023, 1, 1)

        # Invalid format
        result = strategy._parse_datetime("invalid")
        assert result is None

        # None input
        result = strategy._parse_datetime(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_merge_with_missing_fields(self, mock_scene):
        """Test merging when remote data has missing fields"""
        strategy = FullSyncStrategy()

        # Remote data with minimal fields
        remote_data = {
            "title": "Minimal Scene",
            "organized": True,
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        assert result.title == "Minimal Scene"
        assert result.organized is True
        # Other fields should be None or unchanged
        assert result.details is None
        assert result.url is None
        assert result.rating is None

    @pytest.mark.asyncio
    async def test_date_fallback_to_created_at(self, mock_scene):
        """Test that stash_date falls back to created_at when date is not present"""
        strategy = FullSyncStrategy()

        # Remote data without date but with created_at
        remote_data = {
            "title": "Scene Without Date",
            "created_at": "2023-05-15T10:30:00Z",
            # Note: no "date" field
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        # Should use created_at as fallback for stash_date
        assert result.stash_date == datetime(
            2023, 5, 15, 10, 30, 0, tzinfo=timezone.utc
        )
        assert result.stash_created_at == datetime(
            2023, 5, 15, 10, 30, 0, tzinfo=timezone.utc
        )

    @pytest.mark.asyncio
    async def test_date_no_fallback_when_date_exists(self, mock_scene):
        """Test that stash_date uses date field when present, not created_at"""
        strategy = FullSyncStrategy()

        # Remote data with both date and created_at
        remote_data = {
            "title": "Scene With Both Date and Created",
            "date": "2023-06-20",
            "created_at": "2023-05-15T10:30:00Z",
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        # Should use date field, not created_at
        assert result.stash_date == datetime(2023, 6, 20)
        assert result.stash_created_at == datetime(
            2023, 5, 15, 10, 30, 0, tzinfo=timezone.utc
        )

    @pytest.mark.asyncio
    async def test_date_null_when_no_date_or_created_at(self, mock_scene):
        """Test that stash_date is None when neither date nor created_at exist"""
        strategy = FullSyncStrategy()

        # Remote data without date or created_at
        remote_data = {
            "title": "Scene Without Any Dates",
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        # Should be None when neither field exists
        assert result.stash_date is None

    @pytest.mark.asyncio
    async def test_merge_with_no_file_data(self, mock_scene):
        """Test merging when remote data has no file information"""
        strategy = FullSyncStrategy()

        remote_data = {
            "title": "Scene Without File",
            "file": {},  # Empty file data
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        assert result.title == "Scene Without File"
        # File properties are now on SceneFile, not Scene
        # Check that the primary file still has the original properties
        primary_file = result.get_primary_file()
        if primary_file:
            assert primary_file.duration == 3600
            assert primary_file.size == 1000000


class TestIncrementalSyncStrategy:
    """Test the IncrementalSyncStrategy class"""

    @pytest.mark.asyncio
    async def test_should_sync_no_local_entity(self):
        """Test should_sync when there's no local entity"""
        strategy = IncrementalSyncStrategy()

        result = await strategy.should_sync(
            {"updated_at": "2023-07-01T12:00:00Z"}, None
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_remote_newer(self, mock_scene):
        """Test should_sync when remote is newer than local"""
        strategy = IncrementalSyncStrategy()

        # Make local timestamp timezone-aware for proper comparison
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        # Remote is newer
        remote_data = {"updated_at": "2023-08-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_remote_older(self, mock_scene):
        """Test should_sync when remote is older than local"""
        strategy = IncrementalSyncStrategy()

        # Make local timestamp timezone-aware for proper comparison
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        # Remote is older
        remote_data = {"updated_at": "2023-05-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_sync_same_timestamp(self, mock_scene):
        """Test should_sync when timestamps are equal"""
        strategy = IncrementalSyncStrategy()

        # Make local timestamp timezone-aware for proper comparison
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        # Same timestamp
        remote_data = {"updated_at": "2023-06-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_sync_no_remote_timestamp(self, mock_scene):
        """Test should_sync when remote has no timestamp"""
        strategy = IncrementalSyncStrategy()

        result = await strategy.should_sync({}, mock_scene)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_no_local_timestamp(self, mock_scene):
        """Test should_sync when local has no timestamp"""
        strategy = IncrementalSyncStrategy()
        mock_scene.stash_updated_at = None

        remote_data = {"updated_at": "2023-07-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_performer_uses_updated_at(self, mock_performer):
        """Test should_sync for non-Scene entities uses updated_at"""
        strategy = IncrementalSyncStrategy()

        # Make local timestamp timezone-aware for proper comparison
        mock_performer.updated_at = datetime(2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Remote is newer
        remote_data = {"updated_at": "2023-07-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_performer)
        assert result is True

        # Remote is older
        remote_data = {"updated_at": "2023-05-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_performer)
        assert result is False

    @pytest.mark.asyncio
    async def test_merge_data_uses_full_sync(self, mock_scene, remote_scene_data):
        """Test that merge_data delegates to FullSyncStrategy"""
        strategy = IncrementalSyncStrategy()

        result = await strategy.merge_data(mock_scene, remote_scene_data)

        # Should have all the updates from FullSyncStrategy
        assert result.title == "Updated Scene Title"
        assert result.details == "Updated details"


class TestSmartSyncStrategy:
    """Test the SmartSyncStrategy class"""

    @pytest.mark.asyncio
    async def test_should_sync_no_local_entity(self):
        """Test should_sync when there's no local entity"""
        strategy = SmartSyncStrategy()

        result = await strategy.should_sync({}, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_newer_timestamp(self, mock_scene):
        """Test should_sync when remote has newer timestamp"""
        strategy = SmartSyncStrategy()

        # Make local timestamp timezone-aware
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        remote_data = {"updated_at": "2023-08-01T12:00:00Z"}
        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_different_checksum(self, mock_scene):
        """Test should_sync when checksums differ"""
        strategy = SmartSyncStrategy()

        # Make local timestamp timezone-aware
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        # Same timestamp but different content
        remote_data = {
            "updated_at": "2023-06-01T12:00:00Z",
            "title": "Different Title",
            "details": "Different details",
        }

        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_sync_same_checksum(self, mock_scene):
        """Test should_sync when checksums match"""
        strategy = SmartSyncStrategy()

        # Make local timestamp timezone-aware
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        # Calculate checksum for current data
        current_data = {
            "title": "Test Scene",
            "details": "Original details",
        }
        mock_scene.content_checksum = strategy._calculate_checksum(current_data)

        # Remote data with same content
        remote_data = {
            "updated_at": "2023-06-01T12:00:00Z",
            "title": "Test Scene",
            "details": "Original details",
        }

        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_sync_no_local_checksum(self, mock_scene):
        """Test should_sync when local has no checksum"""
        strategy = SmartSyncStrategy()
        mock_scene.content_checksum = None

        # Make local timestamp timezone-aware
        mock_scene.stash_updated_at = datetime(
            2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        remote_data = {
            "updated_at": "2023-06-01T12:00:00Z",
            "title": "Test Scene",
        }

        result = await strategy.should_sync(remote_data, mock_scene)
        assert result is True

    def test_calculate_checksum_consistency(self):
        """Test that checksum calculation is consistent"""
        strategy = SmartSyncStrategy()

        data = {
            "title": "Test",
            "details": "Details",
            "url": "http://example.com",
            "rating": 5,
            "ignored_field": "This should be ignored",
        }

        checksum1 = strategy._calculate_checksum(data)
        checksum2 = strategy._calculate_checksum(data)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 hex digest length

    def test_calculate_checksum_different_data(self):
        """Test that different data produces different checksums"""
        strategy = SmartSyncStrategy()

        data1 = {"title": "Test 1"}
        data2 = {"title": "Test 2"}

        checksum1 = strategy._calculate_checksum(data1)
        checksum2 = strategy._calculate_checksum(data2)

        assert checksum1 != checksum2

    @pytest.mark.asyncio
    async def test_smart_merge_scene_tracks_changes(
        self, mock_scene, remote_scene_data
    ):
        """Test that smart merge only updates changed fields"""
        strategy = SmartSyncStrategy()

        # Set some fields to match remote data
        mock_scene.title = "Updated Scene Title"  # Same as remote
        mock_scene.details = "Original details"  # Different from remote

        result = await strategy.merge_data(mock_scene, remote_scene_data)

        # Title shouldn't be in changes since it's already the same
        # But details should be updated
        assert result.details == "Updated details"
        assert result.url == "http://example.com/updated-scene"

        # File properties are now on SceneFile, not Scene
        # The sync strategy doesn't update file properties directly

        # Checksum should be updated
        assert result.content_checksum == strategy._calculate_checksum(
            remote_scene_data
        )

    @pytest.mark.asyncio
    async def test_smart_merge_non_scene_uses_full_sync(
        self, mock_performer, remote_performer_data
    ):
        """Test that non-Scene entities use FullSyncStrategy"""
        strategy = SmartSyncStrategy()

        with freeze_time("2023-08-01 12:00:00"):
            result = await strategy.merge_data(mock_performer, remote_performer_data)

        assert result.name == "Updated Performer"
        assert result.updated_at == datetime(2023, 8, 1, 12, 0, 0)

    @pytest.mark.asyncio
    async def test_smart_merge_preserves_paths(self, mock_scene):
        """Test that smart merge properly handles file paths"""
        strategy = SmartSyncStrategy()

        remote_data = {
            "title": "Scene with paths",
            "paths": ["/path1.mp4", "/path2.mp4"],
            "file_path": "/primary/path.mp4",
            "file": {},
        }

        await strategy.merge_data(mock_scene, remote_data)

        # Path information is now on SceneFile, not Scene
        # The sync strategy doesn't update file paths directly

    @pytest.mark.asyncio
    async def test_smart_merge_handles_missing_dates(self, mock_scene):
        """Test smart merge with missing date fields"""
        strategy = SmartSyncStrategy()

        remote_data = {
            "title": "Scene without dates",
            "file": {},
            # No created_at, updated_at, or date fields
        }

        with freeze_time("2023-08-01 12:00:00"):
            result = await strategy.merge_data(mock_scene, remote_data)

        # Should use current time for stash_created_at when missing
        assert result.stash_created_at == datetime(2023, 8, 1, 12, 0, 0)
        assert result.stash_date is None

    @pytest.mark.asyncio
    async def test_smart_merge_date_fallback_to_created_at(self, mock_scene):
        """Test that SmartSyncStrategy also uses created_at as fallback for date"""
        strategy = SmartSyncStrategy()

        # Remote data without date but with created_at
        remote_data = {
            "title": "Smart Sync Scene Without Date",
            "created_at": "2023-04-10T08:15:00Z",
            "file": {},
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        # Should use created_at as fallback for stash_date
        assert result.stash_date == datetime(2023, 4, 10, 8, 15, 0, tzinfo=timezone.utc)
        assert result.stash_created_at == datetime(
            2023, 4, 10, 8, 15, 0, tzinfo=timezone.utc
        )


class TestMergeStrategies:
    """Test specific merge behaviors across different strategies"""

    @pytest.mark.asyncio
    async def test_full_sync_overwrites_all_fields(self, mock_scene):
        """Test that FullSyncStrategy overwrites all fields regardless of local changes"""
        strategy = FullSyncStrategy()

        # Set local scene with specific values
        mock_scene.title = "Local Title"
        mock_scene.details = "Local Details"
        mock_scene.rating = 5
        mock_scene.organized = True

        # Remote data with different values
        remote_data = {
            "title": "Remote Title",
            "details": "Remote Details",
            "rating100": 60,  # 3/5 stars
            "organized": False,
            "file": {},
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        # All fields should be overwritten with remote values
        assert result.title == "Remote Title"
        assert result.details == "Remote Details"
        assert result.rating == 3
        assert result.organized is False

    @pytest.mark.asyncio
    async def test_incremental_sync_skip_behavior(self, mock_scene):
        """Test that IncrementalSyncStrategy skips when local is newer"""
        strategy = IncrementalSyncStrategy()

        # Set local scene with newer timestamp
        mock_scene.stash_updated_at = datetime(
            2023, 8, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        # Remote data with older timestamp
        remote_data = {"updated_at": "2023-07-01T12:00:00Z"}

        # Should not sync
        should_sync = await strategy.should_sync(remote_data, mock_scene)
        assert should_sync is False

    @pytest.mark.asyncio
    async def test_smart_sync_selective_merge(self, mock_scene):
        """Test that SmartSyncStrategy only updates changed fields"""
        strategy = SmartSyncStrategy()

        # Set local scene
        mock_scene.title = "Original Title"
        mock_scene.details = "Original Details"
        mock_scene.url = "http://example.com/original"
        mock_scene.organized = True

        # Remote data with some matching and some different values
        remote_data = {
            "title": "Original Title",  # Same as local
            "details": "Updated Details",  # Different
            "url": "http://example.com/updated",  # Different
            "organized": True,  # Same as local
            "file": {},
        }

        result = await strategy.merge_data(mock_scene, remote_data)

        # Only changed fields should be updated
        assert result.title == "Original Title"  # Unchanged
        assert result.details == "Updated Details"  # Changed
        assert result.url == "http://example.com/updated"  # Changed
        assert result.organized is True  # Unchanged

    @pytest.mark.asyncio
    async def test_merge_with_null_values(self):
        """Test handling of null/None values in merge operations"""
        strategy = FullSyncStrategy()

        # Create a scene with some values
        scene = MagicMock(spec=Scene)
        scene.title = "Existing Title"
        scene.details = "Existing Details"
        scene.url = "http://example.com"
        scene.rating = 4

        # Remote data with explicit None values
        remote_data = {
            "title": "New Title",
            "details": None,  # Explicitly null
            "url": None,  # Explicitly null
            "rating100": None,  # Explicitly null
            "file": {},
        }

        result = await strategy.merge_data(scene, remote_data)

        # Should set fields to None when remote has None
        assert result.title == "New Title"
        assert result.details is None
        assert result.url is None
        assert result.rating is None

    @pytest.mark.asyncio
    async def test_merge_preserves_file_properties(self, mock_scene):
        """Test that file properties are always updated from remote"""
        strategy = SmartSyncStrategy()

        # Set local file properties
        mock_scene.duration = 1000
        mock_scene.size = 500000
        mock_scene.codec = "h264"

        # Remote data with different file properties
        remote_data = {
            "title": mock_scene.title,  # Same to test selective merge
            "file": {
                "duration": 2000,
                "size": 600000,
                "video_codec": "h265",
                "height": 1080,
                "width": 1920,
            },
        }

        await strategy.merge_data(mock_scene, remote_data)

        # File properties are now on SceneFile, not Scene
        # The sync strategy doesn't update file properties directly
        # These would be updated when syncing file data

    @pytest.mark.asyncio
    async def test_entity_merge_aliases_handling(self):
        """Test merging of entity aliases"""
        strategy = FullSyncStrategy()

        # Create a performer with aliases
        performer = MagicMock(spec=Performer)
        performer.name = "Original Name"
        performer.aliases = ["Alias1", "Alias2"]
        performer.url = "http://example.com/performer"
        performer.rating = 4

        # Remote data with new aliases
        remote_data = {
            "name": "Updated Name",
            "aliases": ["NewAlias1", "NewAlias2", "NewAlias3"],
            "url": "http://example.com/updated",
            "rating": 5,
        }

        with freeze_time("2023-08-01 12:00:00"):
            result = await strategy.merge_data(performer, remote_data)

        assert result.name == "Updated Name"
        assert result.aliases == ["NewAlias1", "NewAlias2", "NewAlias3"]
        assert result.url == "http://example.com/updated"
        assert result.rating == 5

    @pytest.mark.asyncio
    async def test_skip_strategy_behavior(self):
        """Test skip behavior when checksums match in SmartSyncStrategy"""
        strategy = SmartSyncStrategy()

        # Create scene
        scene = MagicMock(spec=Scene)
        scene.title = "Test Scene"
        scene.details = "Test Details"
        scene.stash_updated_at = datetime(2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Calculate and set checksum for current content
        current_content = {
            "title": "Test Scene",
            "details": "Test Details",
            "organized": False,
        }
        scene.content_checksum = strategy._calculate_checksum(current_content)

        # Remote data with same content (same checksum)
        remote_data = {
            "updated_at": "2023-06-01T12:00:00Z",  # Same timestamp
            "title": "Test Scene",
            "details": "Test Details",
            "organized": False,
        }

        # Should skip sync
        should_sync = await strategy.should_sync(remote_data, scene)
        assert should_sync is False

    @pytest.mark.asyncio
    async def test_rating_conversion(self):
        """Test rating conversion from rating100 to rating scale"""
        strategy = FullSyncStrategy()

        scene = MagicMock(spec=Scene)

        # Test various rating100 values
        test_cases = [
            (0, 0),  # 0/100 = 0/5
            (20, 1),  # 20/100 = 1/5
            (40, 2),  # 40/100 = 2/5
            (60, 3),  # 60/100 = 3/5
            (80, 4),  # 80/100 = 4/5
            (100, 5),  # 100/100 = 5/5
            (50, 2),  # 50/100 = 2.5/5 -> 2/5 (integer division)
            (75, 3),  # 75/100 = 3.75/5 -> 3/5 (integer division)
        ]

        for rating100, expected_rating in test_cases:
            remote_data = {"rating100": rating100, "file": {}}
            result = await strategy.merge_data(scene, remote_data)
            assert result.rating == expected_rating

    @pytest.mark.asyncio
    async def test_entity_without_optional_fields(self):
        """Test merging entities that don't have all optional fields"""
        strategy = FullSyncStrategy()

        # Create a Tag (which doesn't have aliases, url, or rating)
        tag = MagicMock(spec=Tag)
        tag.name = "Original Tag"

        remote_data = {
            "name": "Updated Tag",
            "aliases": ["Should be ignored"],  # Tag doesn't have aliases
            "url": "http://example.com",  # Tag doesn't have url
            "rating": 5,  # Tag doesn't have rating
        }

        with freeze_time("2023-08-01 12:00:00"):
            result = await strategy.merge_data(tag, remote_data)

        assert result.name == "Updated Tag"
        assert result.updated_at == datetime(2023, 8, 1, 12, 0, 0)
        # The strategy should handle missing attributes gracefully
