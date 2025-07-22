"""Tests for scene sync utilities."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scene
from app.services.stash_service import StashService
from app.services.sync.scene_sync_utils import SceneSyncUtils
from tests.helpers import create_test_scene

# Using create_test_scene from tests.helpers


@pytest.fixture
def mock_stash_service():
    """Create a mock StashService."""
    service = AsyncMock(spec=StashService)
    return service


@pytest.fixture
def scene_sync_utils(mock_stash_service):
    """Create a SceneSyncUtils instance with mocked dependencies."""
    return SceneSyncUtils(stash_service=mock_stash_service)


@pytest.fixture
def sample_stash_scene():
    """Sample scene data from Stash."""
    return {
        "id": "scene123",
        "title": "Test Scene",
        "details": "Scene details",
        "url": "https://example.com/scene",
        "rating": 5,
        "organized": True,
        "paths": ["/path/to/scene.mp4"],
        "file": {
            "duration": 1800.5,
            "size": 1073741824,
            "height": 1080,
            "width": 1920,
            "frame_rate": 30.0,
            "bitrate": 5000000,
            "video_codec": "h264",
        },
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-02T12:00:00Z",
        "date": "2024-01-01",
        "studio": {
            "id": "studio123",
            "name": "Test Studio",
            "url": "https://example.com/studio",
        },
        "performers": [
            {
                "id": "performer123",
                "name": "Test Performer",
                "gender": "MALE",
                "url": "https://example.com/performer",
                "image_path": "https://example.com/performer.jpg",
                "aliases": ["Alias 1", "Alias 2"],
            }
        ],
        "tags": [
            {"id": "tag123", "name": "Test Tag", "description": "Tag description"}
        ],
    }


@pytest.fixture
def sample_scene_minimal():
    """Minimal scene data from Stash."""
    return {
        "id": "scene456",
        "title": "",
        "details": "",
        "url": "",
        "organized": False,
        "paths": [],
        "file": {},
    }


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


class TestSceneSyncUtils:
    """Test cases for SceneSyncUtils."""

    @pytest.mark.asyncio
    async def test_sync_scenes_by_ids_success(
        self, scene_sync_utils, mock_stash_service, sample_stash_scene, mock_db_session
    ):
        """Test syncing multiple scenes by IDs."""
        # Setup
        scene_ids = ["scene123", "scene456"]
        mock_stash_service.get_scene.side_effect = [
            sample_stash_scene,
            sample_stash_scene,
        ]

        # Mock database queries
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        # Execute
        with patch.object(
            scene_sync_utils, "sync_single_scene", new_callable=AsyncMock
        ) as mock_sync:
            mock_scene = MagicMock(spec=Scene)
            mock_sync.return_value = mock_scene

            result = await scene_sync_utils.sync_scenes_by_ids(
                scene_ids, mock_db_session
            )

        # Verify
        assert len(result) == 2
        assert mock_stash_service.get_scene.call_count == 2
        assert mock_sync.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_scenes_by_ids_scene_not_found(
        self, scene_sync_utils, mock_stash_service, mock_db_session
    ):
        """Test syncing when scene not found in Stash."""
        # Setup
        scene_ids = ["scene123"]
        mock_stash_service.get_scene.return_value = None

        # Execute
        result = await scene_sync_utils.sync_scenes_by_ids(scene_ids, mock_db_session)

        # Verify
        assert len(result) == 0
        assert mock_stash_service.get_scene.call_count == 1

    @pytest.mark.asyncio
    async def test_sync_scenes_by_ids_error_handling(
        self, scene_sync_utils, mock_stash_service, mock_db_session
    ):
        """Test error handling during scene sync."""
        # Setup
        scene_ids = ["scene123", "scene456"]
        mock_stash_service.get_scene.side_effect = [
            Exception("API error"),
            {"id": "scene456", "title": "Valid Scene"},
        ]

        # Execute
        with patch.object(
            scene_sync_utils, "sync_single_scene", new_callable=AsyncMock
        ) as mock_sync:
            mock_scene = MagicMock(spec=Scene)
            mock_sync.return_value = mock_scene

            result = await scene_sync_utils.sync_scenes_by_ids(
                scene_ids, mock_db_session
            )

        # Verify - should continue with second scene despite first failing
        assert len(result) == 1
        assert mock_stash_service.get_scene.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_single_scene_create_new(
        self, scene_sync_utils, sample_stash_scene, mock_db_session
    ):
        """Test creating a new scene."""
        # Setup - no existing scene
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Mock the entity creation methods to avoid model initialization issues
        with patch.object(
            scene_sync_utils, "_sync_scene_relationships", new_callable=AsyncMock
        ):
            # Execute
            result = await scene_sync_utils.sync_single_scene(
                sample_stash_scene, mock_db_session
            )

        # Verify
        assert result is not None
        assert result.id == "scene123"
        assert result.title == "Test Scene"
        assert result.details == "Scene details"
        assert result.url == "https://example.com/scene"
        assert result.rating == 5
        assert result.organized is True
        # File attributes should be in the files relationship
        assert len(result.files) > 0
        primary_file = result.get_primary_file()
        assert primary_file is not None
        assert primary_file.duration == 1800.5
        assert primary_file.size == 1073741824
        assert primary_file.height == 1080
        assert primary_file.width == 1920
        assert primary_file.frame_rate == 30.0
        assert primary_file.bit_rate == 5000000
        assert primary_file.video_codec == "h264"
        assert mock_db_session.add.called
        assert mock_db_session.flush.called

    @pytest.mark.asyncio
    async def test_sync_single_scene_update_existing(
        self, scene_sync_utils, sample_stash_scene, mock_db_session
    ):
        """Test updating an existing scene."""
        # Setup - existing scene
        existing_scene = create_test_scene(
            id="scene123", title="Old Title", details="Old details"
        )
        existing_scene.performers = []
        existing_scene.tags = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_scene
        mock_db_session.execute.return_value = mock_result

        # Mock the entity creation methods to avoid model initialization issues
        with patch.object(
            scene_sync_utils, "_sync_scene_relationships", new_callable=AsyncMock
        ):
            # Execute
            result = await scene_sync_utils.sync_single_scene(
                sample_stash_scene, mock_db_session, update_existing=True
            )

        # Verify
        assert result is not None
        assert result.id == "scene123"
        assert result.title == "Test Scene"  # Updated
        assert result.details == "Scene details"  # Updated
        assert mock_db_session.flush.called

    @pytest.mark.asyncio
    async def test_sync_single_scene_skip_existing(
        self, scene_sync_utils, sample_stash_scene, mock_db_session
    ):
        """Test skipping update for existing scene."""
        # Setup - existing scene
        existing_scene = create_test_scene(
            id="scene123", title="Old Title", details="Old details"
        )
        existing_scene.performers = []
        existing_scene.tags = []
        existing_scene.studio = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_scene
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await scene_sync_utils.sync_single_scene(
            sample_stash_scene, mock_db_session, update_existing=False
        )

        # Verify
        assert result is not None
        assert result.id == "scene123"
        assert result.title == "Old Title"  # Not updated
        assert result.details == "Old details"  # Not updated

    @pytest.mark.asyncio
    async def test_sync_single_scene_missing_id(
        self, scene_sync_utils, mock_db_session
    ):
        """Test handling scene without ID."""
        # Setup
        stash_scene = {"title": "No ID Scene"}

        # Execute
        result = await scene_sync_utils.sync_single_scene(stash_scene, mock_db_session)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_update_scene_fields_complete(
        self, scene_sync_utils, sample_stash_scene
    ):
        """Test updating all scene fields."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")

        # Execute
        await scene_sync_utils._update_scene_fields(scene, sample_stash_scene)

        # Verify all fields updated
        assert scene.title == "Test Scene"
        assert scene.details == "Scene details"
        assert scene.url == "https://example.com/scene"
        assert scene.rating == 5
        assert scene.organized is True
        # File attributes should be updated in the files relationship
        assert len(scene.files) > 0
        primary_file = scene.get_primary_file()
        assert primary_file is not None
        assert primary_file.path == "/path/to/scene.mp4"
        assert primary_file.duration == 1800.5
        assert primary_file.size == 1073741824
        assert primary_file.height == 1080
        assert primary_file.width == 1920
        assert primary_file.frame_rate == 30.0
        assert primary_file.bit_rate == 5000000
        assert primary_file.video_codec == "h264"
        assert scene.stash_created_at is not None
        assert scene.stash_updated_at is not None
        assert scene.stash_date is not None
        assert scene.content_checksum is not None

    @pytest.mark.asyncio
    async def test_update_scene_fields_minimal(
        self, scene_sync_utils, sample_scene_minimal
    ):
        """Test updating scene with minimal data."""
        # Setup
        scene = create_test_scene(id="scene456", title="")

        # Execute
        await scene_sync_utils._update_scene_fields(scene, sample_scene_minimal)

        # Verify defaults
        assert scene.title == ""
        assert scene.details == ""
        assert scene.url == ""
        assert scene.rating is None
        assert scene.organized is False
        # File attributes should be None in the files relationship
        if scene.files:
            primary_file = scene.get_primary_file()
            assert primary_file is None or primary_file.duration is None
            assert primary_file is None or primary_file.size is None

    @pytest.mark.asyncio
    async def test_sync_scene_relationships_complete(
        self, scene_sync_utils, sample_stash_scene, mock_db_session
    ):
        """Test syncing all scene relationships."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")
        scene.performers = []
        scene.tags = []

        # Mock the individual entity creation methods
        with (
            patch.object(
                scene_sync_utils, "_get_or_create_studio", new_callable=AsyncMock
            ) as mock_studio,
            patch.object(
                scene_sync_utils, "_get_or_create_performer", new_callable=AsyncMock
            ) as mock_performer,
            patch.object(
                scene_sync_utils, "_get_or_create_tag", new_callable=AsyncMock
            ) as mock_tag,
        ):

            # Create simple mock objects
            studio = MagicMock()
            studio.id = "studio123"
            performer = MagicMock()
            performer.id = "performer123"
            tag = MagicMock()
            tag.id = "tag123"

            mock_studio.return_value = studio
            mock_performer.return_value = performer
            mock_tag.return_value = tag

            # Execute
            await scene_sync_utils._sync_scene_relationships(
                scene, sample_stash_scene, mock_db_session
            )

        # Verify
        assert scene.studio is not None
        assert scene.studio.id == "studio123"
        assert len(scene.performers) == 1
        assert scene.performers[0].id == "performer123"
        assert len(scene.tags) == 1
        assert scene.tags[0].id == "tag123"

    @pytest.mark.asyncio
    async def test_sync_scene_relationships_no_relations(
        self, scene_sync_utils, mock_db_session
    ):
        """Test syncing scene with no relationships."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")
        scene.performers = [MagicMock()]  # Has existing
        scene.tags = [MagicMock()]  # Has existing
        scene.studio = MagicMock()  # Has existing

        stash_scene = {
            "id": "scene123",
            "title": "Test Scene",
            # No studio, performers, or tags
        }

        # Execute
        await scene_sync_utils._sync_scene_relationships(
            scene, stash_scene, mock_db_session
        )

        # Verify - all relationships cleared
        assert scene.studio is None
        assert len(scene.performers) == 0
        assert len(scene.tags) == 0

    @pytest.mark.asyncio
    async def test_get_or_create_studio_no_id(self, scene_sync_utils, mock_db_session):
        """Test handling studio without ID."""
        # Setup
        studio_data = {"name": "No ID Studio"}

        # Execute
        result = await scene_sync_utils._get_or_create_studio(
            studio_data, mock_db_session
        )

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_content_checksum_calculation(self, scene_sync_utils):
        """Test content checksum is calculated consistently."""
        # Setup
        scene1 = create_test_scene(id="scene1", title="Scene 1")
        scene2 = create_test_scene(id="scene2", title="Scene 2")

        stash_scene = {
            "title": "Test Scene",
            "details": "Details",
            "url": "https://example.com",
            "rating": 5,
            "paths": ["/path/1", "/path/2"],
        }

        # Execute
        await scene_sync_utils._update_scene_fields(scene1, stash_scene)
        await scene_sync_utils._update_scene_fields(scene2, stash_scene)

        # Verify - same content produces same checksum
        assert scene1.content_checksum == scene2.content_checksum

        # Change content
        stash_scene["title"] = "Different Title"
        await scene_sync_utils._update_scene_fields(scene2, stash_scene)

        # Verify - different content produces different checksum
        assert scene1.content_checksum != scene2.content_checksum

    @pytest.mark.asyncio
    async def test_timestamp_parsing(self, scene_sync_utils):
        """Test timestamp parsing from Stash format."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")

        stash_scene = {
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-02T13:30:45Z",
            "date": "2024-01-03",
        }

        # Execute
        await scene_sync_utils._update_scene_fields(scene, stash_scene)

        # Verify
        assert scene.stash_created_at == datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        assert scene.stash_updated_at == datetime(
            2024, 1, 2, 13, 30, 45, tzinfo=timezone.utc
        )
        assert scene.stash_date == datetime(2024, 1, 3, 0, 0, 0)

    @pytest.mark.asyncio
    async def test_sync_multiple_performers(self, scene_sync_utils, mock_db_session):
        """Test syncing scene with multiple performers."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")
        scene.performers = []
        scene.tags = []

        stash_scene = {
            "performers": [
                {"id": "p1", "name": "Performer 1"},
                {"id": "p2", "name": "Performer 2"},
                {"id": "p3", "name": "Performer 3"},
            ]
        }

        # Mock the get_or_create_performer method
        with patch.object(
            scene_sync_utils, "_get_or_create_performer", new_callable=AsyncMock
        ) as mock_get:
            performers = []
            for i in range(1, 4):
                p = MagicMock()
                p.id = f"p{i}"
                p.name = f"Performer {i}"
                performers.append(p)

            mock_get.side_effect = performers

            # Execute
            await scene_sync_utils._sync_scene_relationships(
                scene, stash_scene, mock_db_session
            )

        # Verify
        assert len(scene.performers) == 3
        assert scene.performers[0].id == "p1"
        assert scene.performers[1].id == "p2"
        assert scene.performers[2].id == "p3"

    @pytest.mark.asyncio
    async def test_sync_multiple_tags(self, scene_sync_utils, mock_db_session):
        """Test syncing scene with multiple tags."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")
        scene.performers = []
        scene.tags = []

        stash_scene = {
            "tags": [
                {"id": "t1", "name": "Tag 1"},
                {"id": "t2", "name": "Tag 2"},
                {"id": "t3", "name": "Tag 3"},
                {"id": "t4", "name": "Tag 4"},
            ]
        }

        # Mock the get_or_create_tag method
        with patch.object(
            scene_sync_utils, "_get_or_create_tag", new_callable=AsyncMock
        ) as mock_get:
            tags = []
            for i in range(1, 5):
                t = MagicMock()
                t.id = f"t{i}"
                t.name = f"Tag {i}"
                tags.append(t)

            mock_get.side_effect = tags

            # Execute
            await scene_sync_utils._sync_scene_relationships(
                scene, stash_scene, mock_db_session
            )

        # Verify
        assert len(scene.tags) == 4
        for i, tag in enumerate(scene.tags):
            assert tag.id == f"t{i+1}"
            assert tag.name == f"Tag {i+1}"

    @pytest.mark.asyncio
    async def test_clear_existing_relationships(
        self, scene_sync_utils, mock_db_session
    ):
        """Test that existing relationships are cleared before adding new ones."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")
        # Add existing relationships
        old_performer1 = MagicMock()
        old_performer1.id = "old1"
        old_performer2 = MagicMock()
        old_performer2.id = "old2"
        scene.performers = [old_performer1, old_performer2]

        old_tag = MagicMock()
        old_tag.id = "old1"
        scene.tags = [old_tag]

        stash_scene = {
            "performers": [{"id": "new1", "name": "New Performer"}],
            "tags": [{"id": "new1", "name": "New Tag"}],
        }

        # Mock the entity creation methods
        with (
            patch.object(
                scene_sync_utils, "_get_or_create_performer", new_callable=AsyncMock
            ) as mock_performer,
            patch.object(
                scene_sync_utils, "_get_or_create_tag", new_callable=AsyncMock
            ) as mock_tag,
        ):

            new_performer = MagicMock()
            new_performer.id = "new1"
            new_tag = MagicMock()
            new_tag.id = "new1"

            mock_performer.return_value = new_performer
            mock_tag.return_value = new_tag

            # Execute
            await scene_sync_utils._sync_scene_relationships(
                scene, stash_scene, mock_db_session
            )

        # Verify - old relationships cleared, new ones added
        assert len(scene.performers) == 1
        assert scene.performers[0].id == "new1"
        assert len(scene.tags) == 1
        assert scene.tags[0].id == "new1"

    @pytest.mark.asyncio
    async def test_last_synced_timestamp(
        self, scene_sync_utils, sample_stash_scene, mock_db_session
    ):
        """Test that last_synced timestamp is updated."""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Mock the entity creation methods to avoid model initialization issues
        with patch.object(
            scene_sync_utils, "_sync_scene_relationships", new_callable=AsyncMock
        ):
            # Execute
            before_sync = datetime.utcnow()
            result = await scene_sync_utils.sync_single_scene(
                sample_stash_scene, mock_db_session
            )
            after_sync = datetime.utcnow()

        # Verify
        assert result is not None
        assert result.last_synced is not None
        assert before_sync <= result.last_synced <= after_sync

    @pytest.mark.asyncio
    async def test_scene_entity_filtering(self, scene_sync_utils, mock_db_session):
        """Test that None entities are filtered out when syncing relationships."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")
        scene.performers = []
        scene.tags = []

        stash_scene = {
            "performers": [
                {"id": "p1", "name": "Performer 1"},
                {"id": "", "name": "Invalid Performer"},  # Invalid - no ID
                {"id": "p3", "name": "Performer 3"},
            ],
            "tags": [
                {"id": "t1", "name": "Tag 1"},
                {"name": "Tag without ID"},  # Invalid - no ID
                {"id": "t3", "name": "Tag 3"},
            ],
        }

        # Mock the entity creation methods to return None for invalid entities
        with (
            patch.object(
                scene_sync_utils, "_get_or_create_performer", new_callable=AsyncMock
            ) as mock_performer,
            patch.object(
                scene_sync_utils, "_get_or_create_tag", new_callable=AsyncMock
            ) as mock_tag,
        ):

            # Create performers - None for invalid ones
            p1 = MagicMock()
            p1.id = "p1"
            p3 = MagicMock()
            p3.id = "p3"
            mock_performer.side_effect = [p1, None, p3]  # None for empty ID

            # Create tags - None for invalid ones
            t1 = MagicMock()
            t1.id = "t1"
            t3 = MagicMock()
            t3.id = "t3"
            mock_tag.side_effect = [t1, None, t3]  # None for missing ID

            # Execute
            await scene_sync_utils._sync_scene_relationships(
                scene, stash_scene, mock_db_session
            )

        # Verify - only valid entities are added
        assert len(scene.performers) == 2
        assert scene.performers[0].id == "p1"
        assert scene.performers[1].id == "p3"
        assert len(scene.tags) == 2
        assert scene.tags[0].id == "t1"
        assert scene.tags[1].id == "t3"

    @pytest.mark.asyncio
    async def test_update_scene_fields_date_parsing_variants(self, scene_sync_utils):
        """Test various date format parsing."""
        # Setup
        scene = create_test_scene(id="scene123", title="Test Scene")

        # Test different date formats
        test_cases = [
            {
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T23:59:59Z",
                "date": "2024-01-03",
            },
            {
                "created_at": "2024-06-15T12:30:45Z",
                "updated_at": "2024-12-31T23:59:59Z",
                "date": "2024-07-01",
            },
        ]

        for stash_scene in test_cases:
            # Execute
            await scene_sync_utils._update_scene_fields(scene, stash_scene)

            # Verify all dates are parsed correctly
            assert scene.stash_created_at is not None
            assert scene.stash_updated_at is not None
            assert scene.stash_date is not None
            assert isinstance(scene.stash_created_at, datetime)
            assert isinstance(scene.stash_updated_at, datetime)
            assert isinstance(scene.stash_date, datetime)

    @pytest.mark.asyncio
    async def test_get_or_create_performer_no_id(
        self, scene_sync_utils, mock_db_session
    ):
        """Test handling performer without ID."""
        # Setup
        performer_data = {"name": "No ID Performer"}

        # Execute
        result = await scene_sync_utils._get_or_create_performer(
            performer_data, mock_db_session
        )

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_tag_no_id(self, scene_sync_utils, mock_db_session):
        """Test handling tag without ID."""
        # Setup
        tag_data = {"name": "No ID Tag"}

        # Execute
        result = await scene_sync_utils._get_or_create_tag(tag_data, mock_db_session)

        # Verify
        assert result is None
