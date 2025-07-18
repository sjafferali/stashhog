from datetime import datetime
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from app.models import Performer, Scene, Studio, Tag
from app.services.sync.conflicts import (
    ConflictResolver,
    ConflictStrategy,
    ConflictType,
)


@pytest.fixture
def conflict_resolver():
    """Create a ConflictResolver instance with default strategy"""
    return ConflictResolver(default_strategy=ConflictStrategy.REMOTE_WINS)


@pytest.fixture
def mock_scene():
    """Create a mock scene with test data"""
    scene = MagicMock(spec=Scene)
    scene.id = "scene-123"
    scene.title = "Local Title"
    scene.details = "Local details"
    scene.url = "http://local.com/scene"
    scene.rating = 4
    scene.organized = True
    scene.duration = 3600
    scene.size = 1000000
    scene.height = 1080
    scene.width = 1920
    scene.framerate = 30
    scene.bitrate = 5000
    scene.codec = "h264"

    # Mock relationships
    perf1 = MagicMock()
    perf1.id = "perf-1"
    perf2 = MagicMock()
    perf2.id = "perf-2"
    scene.performers = [perf1, perf2]

    tag1 = MagicMock()
    tag1.id = "tag-1"
    tag2 = MagicMock()
    tag2.id = "tag-2"
    scene.tags = [tag1, tag2]

    studio = MagicMock()
    studio.id = "studio-1"
    scene.studio = studio

    return scene


@pytest.fixture
def remote_scene_data():
    """Create remote scene data that conflicts with local"""
    return {
        "id": "scene-123",
        "title": "Remote Title",
        "details": "Remote details",
        "url": "http://remote.com/scene",
        "rating": 5,
        "organized": False,
        "file": {
            "duration": 3700,
            "size": 1100000,
            "height": 2160,
            "width": 3840,
            "framerate": 60,
            "bitrate": 6000,
            "video_codec": "h265",
        },
        "performers": [
            {"id": "perf-1"},  # Same
            {"id": "perf-3"},  # Different
        ],
        "tags": [
            {"id": "tag-2"},  # Same
            {"id": "tag-3"},  # Different
        ],
        "studio": {"id": "studio-2"},  # Different
    }


@pytest.fixture
def mock_performer():
    """Create a mock performer"""
    performer = MagicMock(spec=Performer)
    performer.id = "performer-123"
    performer.name = "Local Performer"
    performer.aliases = ["Local Alias"]
    performer.gender = "FEMALE"
    performer.birthdate = "1990-01-01"
    performer.url = "http://local.com/performer"
    performer.rating = 4
    return performer


@pytest.fixture
def remote_performer_data():
    """Create remote performer data"""
    return {
        "id": "performer-123",
        "name": "Remote Performer",
        "aliases": ["Remote Alias 1", "Remote Alias 2"],
        "gender": "MALE",
        "birthdate": "1990-01-02",
        "url": "http://remote.com/performer",
        "rating": 5,
    }


@pytest.fixture
def mock_tag():
    """Create a mock tag"""
    tag = MagicMock(spec=Tag)
    tag.id = "tag-123"
    tag.name = "Local Tag"
    return tag


@pytest.fixture
def mock_studio():
    """Create a mock studio"""
    studio = MagicMock(spec=Studio)
    studio.id = "studio-123"
    studio.name = "Local Studio"
    studio.url = "http://local.com/studio"
    studio.details = "Local studio details"
    studio.rating = 3
    return studio


class TestConflictResolver:
    """Test the ConflictResolver class"""

    def test_init_with_default_strategy(self):
        """Test initialization with custom default strategy"""
        resolver = ConflictResolver(default_strategy=ConflictStrategy.LOCAL_WINS)
        assert resolver.default_strategy == ConflictStrategy.LOCAL_WINS
        assert resolver.conflict_log == []

    def test_detect_scene_field_changes(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test detecting field changes in scenes"""
        changes = conflict_resolver.detect_changes(mock_scene, remote_scene_data)

        # Check basic field changes
        assert "title" in changes
        assert changes["title"]["local"] == "Local Title"
        assert changes["title"]["remote"] == "Remote Title"
        assert changes["title"]["type"] == ConflictType.FIELD_MISMATCH

        assert "details" in changes
        assert changes["details"]["local"] == "Local details"
        assert changes["details"]["remote"] == "Remote details"

        assert "rating" in changes
        assert changes["rating"]["local"] == 4
        assert changes["rating"]["remote"] == 5

        assert "organized" in changes
        assert changes["organized"]["local"] is True
        assert changes["organized"]["remote"] is False

    def test_detect_scene_file_changes(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test detecting file property changes in scenes"""
        changes = conflict_resolver.detect_changes(mock_scene, remote_scene_data)

        # Check file property changes
        assert "file.duration" in changes
        assert changes["file.duration"]["local"] == 3600
        assert changes["file.duration"]["remote"] == 3700

        assert "file.size" in changes
        assert changes["file.size"]["local"] == 1000000
        assert changes["file.size"]["remote"] == 1100000

        assert "file.codec" in changes
        assert changes["file.codec"]["local"] == "h264"
        assert changes["file.codec"]["remote"] == "h265"

    def test_detect_scene_relationship_changes(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test detecting relationship changes in scenes"""
        changes = conflict_resolver.detect_changes(mock_scene, remote_scene_data)

        # Check performer changes
        assert "performers" in changes
        assert set(changes["performers"]["local"]) == {"perf-1", "perf-2"}
        assert set(changes["performers"]["remote"]) == {"perf-1", "perf-3"}
        assert changes["performers"]["added"] == ["perf-3"]
        assert changes["performers"]["removed"] == ["perf-2"]
        assert changes["performers"]["type"] == ConflictType.RELATIONSHIP_MISMATCH

        # Check tag changes
        assert "tags" in changes
        assert set(changes["tags"]["local"]) == {"tag-1", "tag-2"}
        assert set(changes["tags"]["remote"]) == {"tag-2", "tag-3"}
        assert changes["tags"]["added"] == ["tag-3"]
        assert changes["tags"]["removed"] == ["tag-1"]

        # Check studio change
        assert "studio" in changes
        assert changes["studio"]["local"] == "studio-1"
        assert changes["studio"]["remote"] == "studio-2"

    def test_detect_no_changes(self, conflict_resolver, mock_scene):
        """Test when there are no changes"""
        # Remote data matches local
        remote_data = {
            "title": "Local Title",
            "details": "Local details",
            "url": "http://local.com/scene",
            "rating": 4,
            "organized": True,
            "file": {
                "duration": 3600,
                "size": 1000000,
                "height": 1080,
                "width": 1920,
                "framerate": 30,
                "bitrate": 5000,
                "video_codec": "h264",
            },
            "performers": [{"id": "perf-1"}, {"id": "perf-2"}],
            "tags": [{"id": "tag-1"}, {"id": "tag-2"}],
            "studio": {"id": "studio-1"},
        }

        changes = conflict_resolver.detect_changes(mock_scene, remote_data)
        assert changes == {}

    def test_resolve_scene_conflict_remote_wins(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test resolving conflicts with REMOTE_WINS strategy"""
        result = conflict_resolver.resolve_scene_conflict(
            mock_scene, remote_scene_data, ConflictStrategy.REMOTE_WINS
        )

        # Fields should be updated to remote values
        assert result.title == "Remote Title"
        assert result.details == "Remote details"
        assert result.url == "http://remote.com/scene"
        assert result.rating == 5
        assert result.organized is False

        # File properties should be updated
        assert result.duration == 3700
        assert result.size == 1100000
        assert result.codec == "h265"

        # Conflict should be logged
        assert len(conflict_resolver.conflict_log) == 1
        log_entry = conflict_resolver.conflict_log[0]
        assert log_entry["entity_type"] == "scene"
        assert log_entry["entity_id"] == "scene-123"
        assert log_entry["strategy"] == "remote_wins"

    def test_resolve_scene_conflict_local_wins(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test resolving conflicts with LOCAL_WINS strategy"""
        # Store original values
        original_title = mock_scene.title
        original_details = mock_scene.details

        result = conflict_resolver.resolve_scene_conflict(
            mock_scene, remote_scene_data, ConflictStrategy.LOCAL_WINS
        )

        # Fields should remain unchanged
        assert result.title == original_title
        assert result.details == original_details
        assert result.rating == 4
        assert result.organized is True

        # Conflict should still be logged
        assert len(conflict_resolver.conflict_log) == 1

    def test_resolve_scene_conflict_merge(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test resolving conflicts with MERGE strategy"""
        result = conflict_resolver.resolve_scene_conflict(
            mock_scene, remote_scene_data, ConflictStrategy.MERGE
        )

        # File properties should always be updated from remote
        assert result.duration == 3700
        assert result.size == 1100000
        assert result.codec == "h265"

        # Other fields depend on manually_edited flag
        # Since our mock doesn't have manually_edited=True, remote wins
        assert result.title == "Remote Title"

    def test_resolve_scene_conflict_manual(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test resolving conflicts with MANUAL strategy"""
        # Add required attributes to mock
        mock_scene.sync_conflict = False
        mock_scene.conflict_data = None

        result = conflict_resolver.resolve_scene_conflict(
            mock_scene, remote_scene_data, ConflictStrategy.MANUAL
        )

        # Scene should be flagged for manual review
        assert result.sync_conflict is True
        assert result.conflict_data is not None
        assert "title" in result.conflict_data

        # Original values should be preserved
        assert result.title == "Local Title"

    def test_detect_performer_changes(
        self, conflict_resolver, mock_performer, remote_performer_data
    ):
        """Test detecting changes in performer fields"""
        changes = conflict_resolver.detect_changes(
            mock_performer, remote_performer_data
        )

        assert "name" in changes
        assert changes["name"]["local"] == "Local Performer"
        assert changes["name"]["remote"] == "Remote Performer"

        assert "aliases" in changes
        assert changes["aliases"]["local"] == ["Local Alias"]
        assert changes["aliases"]["remote"] == ["Remote Alias 1", "Remote Alias 2"]

        assert "gender" in changes
        assert changes["gender"]["local"] == "FEMALE"
        assert changes["gender"]["remote"] == "MALE"

    def test_detect_tag_changes(self, conflict_resolver, mock_tag):
        """Test detecting changes in tag fields"""
        remote_data = {"name": "Remote Tag"}
        changes = conflict_resolver.detect_changes(mock_tag, remote_data)

        assert "name" in changes
        assert changes["name"]["local"] == "Local Tag"
        assert changes["name"]["remote"] == "Remote Tag"

    def test_detect_studio_changes(self, conflict_resolver, mock_studio):
        """Test detecting changes in studio fields"""
        remote_data = {
            "name": "Remote Studio",
            "url": "http://remote.com/studio",
            "details": "Remote studio details",
            "rating": 5,
        }

        changes = conflict_resolver.detect_changes(mock_studio, remote_data)

        assert "name" in changes
        assert changes["name"]["local"] == "Local Studio"
        assert changes["name"]["remote"] == "Remote Studio"

        assert "rating" in changes
        assert changes["rating"]["local"] == 3
        assert changes["rating"]["remote"] == 5

    @freeze_time("2023-08-01 12:00:00")
    def test_conflict_logging(self, conflict_resolver, mock_scene, remote_scene_data):
        """Test that conflicts are properly logged"""
        conflict_resolver.resolve_scene_conflict(mock_scene, remote_scene_data)

        assert len(conflict_resolver.conflict_log) == 1
        log_entry = conflict_resolver.conflict_log[0]

        assert log_entry["timestamp"] == datetime(2023, 8, 1, 12, 0, 0)
        assert log_entry["entity_type"] == "scene"
        assert log_entry["entity_id"] == "scene-123"
        assert log_entry["resolved"] is True
        assert len(log_entry["changes"]) > 0

    def test_get_conflict_summary(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test getting conflict summary"""
        # Create some conflicts
        conflict_resolver.resolve_scene_conflict(mock_scene, remote_scene_data)
        conflict_resolver.resolve_scene_conflict(
            mock_scene, remote_scene_data, ConflictStrategy.LOCAL_WINS
        )

        summary = conflict_resolver.get_conflict_summary()

        assert summary["total_conflicts"] == 2
        assert summary["by_type"]["scene"] == 2
        assert summary["by_strategy"]["remote_wins"] == 1
        assert summary["by_strategy"]["local_wins"] == 1
        assert len(summary["recent_conflicts"]) == 2

    def test_merge_strategy_with_manually_edited(
        self, conflict_resolver, mock_scene, remote_scene_data
    ):
        """Test merge strategy respects manually_edited flag"""
        # Mark scene as manually edited
        mock_scene.manually_edited = True
        original_title = mock_scene.title

        result = conflict_resolver.resolve_scene_conflict(
            mock_scene, remote_scene_data, ConflictStrategy.MERGE
        )

        # Manual edits should be preserved
        assert result.title == original_title
        # But file properties should still update
        assert result.duration == 3700

    def test_no_conflict_when_no_changes(self, conflict_resolver, mock_scene):
        """Test that no conflict is logged when there are no changes"""
        # Remote data matches local exactly
        remote_data = {
            "title": mock_scene.title,
            "details": mock_scene.details,
            "url": mock_scene.url,
            "rating": mock_scene.rating,
            "organized": mock_scene.organized,
            "file": {
                "duration": mock_scene.duration,
                "size": mock_scene.size,
                "height": mock_scene.height,
                "width": mock_scene.width,
                "framerate": mock_scene.framerate,
                "bitrate": mock_scene.bitrate,
                "video_codec": mock_scene.codec,
            },
            "performers": [{"id": p.id} for p in mock_scene.performers],
            "tags": [{"id": t.id} for t in mock_scene.tags],
            "studio": {"id": mock_scene.studio.id},
        }

        result = conflict_resolver.resolve_scene_conflict(mock_scene, remote_data)

        # No conflict should be logged
        assert len(conflict_resolver.conflict_log) == 0
        assert result == mock_scene

    def test_count_by_field_helper(self, conflict_resolver):
        """Test the _count_by_field helper method"""
        items = [
            {"type": "scene", "strategy": "remote_wins"},
            {"type": "scene", "strategy": "local_wins"},
            {"type": "performer", "strategy": "remote_wins"},
            {"type": "scene", "strategy": "remote_wins"},
        ]

        type_counts = conflict_resolver._count_by_field(items, "type")
        assert type_counts == {"scene": 3, "performer": 1}

        strategy_counts = conflict_resolver._count_by_field(items, "strategy")
        assert strategy_counts == {"remote_wins": 3, "local_wins": 1}

    def test_handle_missing_relationships(self, conflict_resolver, mock_scene):
        """Test handling scenes with no relationships"""
        # Scene with no performers, tags, or studio
        scene = MagicMock(spec=Scene)
        scene.id = "scene-456"
        scene.title = "Scene without relationships"
        scene.performers = []
        scene.tags = []
        scene.studio = None

        remote_data = {
            "title": "Updated title",
            "performers": [{"id": "perf-1"}],
            "tags": [{"id": "tag-1"}],
            "studio": {"id": "studio-1"},
        }

        changes = conflict_resolver.detect_changes(scene, remote_data)

        # Should detect all relationships as additions
        assert changes["performers"]["added"] == ["perf-1"]
        assert changes["performers"]["removed"] == []
        assert changes["tags"]["added"] == ["tag-1"]
        assert changes["tags"]["removed"] == []
        assert changes["studio"]["local"] is None
        assert changes["studio"]["remote"] == "studio-1"
