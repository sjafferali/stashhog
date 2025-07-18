from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Performer, Studio, Tag
from app.services.stash_service import StashService
from app.services.sync.entity_sync import EntitySyncHandler


@pytest.fixture
def mock_stash_service():
    """Create a mock StashService"""
    return MagicMock(spec=StashService)


@pytest.fixture
def mock_strategy():
    """Create a mock SyncStrategy"""
    strategy = MagicMock()
    strategy.should_sync = AsyncMock(return_value=True)
    strategy.merge_data = AsyncMock(side_effect=lambda entity, data: entity)
    return strategy


@pytest.fixture
def entity_sync_handler(mock_stash_service, mock_strategy):
    """Create an EntitySyncHandler instance"""
    return EntitySyncHandler(mock_stash_service, mock_strategy)


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_performer_data():
    """Sample performer data from Stash"""
    return {
        "id": "performer-123",
        "name": "Test Performer",
        "aliases": ["Alias 1", "Alias 2"],
        "gender": "FEMALE",
        "birthdate": "1990-01-01",
        "country": "USA",
        "ethnicity": "Caucasian",
        "hair_color": "Blonde",
        "eye_color": "Blue",
        "height": 170,
        "weight": 60,
        "measurements": "36-24-36",
        "fake_tits": False,
        "career_length": "2010-2020",
        "tattoos": "Butterfly on ankle",
        "piercings": "Ears",
        "url": "http://example.com/performer",
        "twitter": "@performer",
        "instagram": "@performer",
        "details": "Test performer details",
        "rating": 5,
        "favorite": True,
        "ignore_auto_tag": False,
        "image_path": "http://example.com/image.jpg",
        "updated_at": "2023-07-01T12:00:00Z",
    }


@pytest.fixture
def sample_tag_data():
    """Sample tag data from Stash"""
    return {
        "id": "tag-123",
        "name": "Test Tag",
        "aliases": ["Tag Alias 1"],
        "description": "Test tag description",
        "ignore_auto_tag": False,
        "parent": {"id": "parent-tag-123"},
        "updated_at": "2023-07-01T12:00:00Z",
    }


@pytest.fixture
def sample_studio_data():
    """Sample studio data from Stash"""
    return {
        "id": "studio-123",
        "name": "Test Studio",
        "aliases": ["Studio Alias"],
        "url": "http://example.com/studio",
        "details": "Test studio details",
        "rating": 4,
        "favorite": False,
        "ignore_auto_tag": True,
        "parent": {"id": "parent-studio-123"},
        "image_path": "http://example.com/studio.jpg",
        "updated_at": "2023-07-01T12:00:00Z",
    }


class TestEntitySyncHandler:
    """Test the EntitySyncHandler class"""

    @pytest.mark.asyncio
    async def test_sync_performers_success(
        self, entity_sync_handler, mock_db_session, sample_performer_data
    ):
        """Test successful performer synchronization"""
        # Setup mock database response - no existing performer
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Sync single performer
        stats = await entity_sync_handler.sync_performers(
            [sample_performer_data], mock_db_session
        )

        # Verify stats
        assert stats["processed"] == 1
        assert stats["created"] == 1
        assert stats["updated"] == 0
        assert stats["skipped"] == 0
        assert stats["failed"] == 0

        # Verify performer was added to session
        assert mock_db_session.add.called
        assert mock_db_session.flush.called

    @pytest.mark.asyncio
    async def test_sync_performers_update_existing(
        self, entity_sync_handler, mock_db_session, sample_performer_data
    ):
        """Test updating an existing performer"""
        # Create existing performer
        existing_performer = MagicMock(spec=Performer)
        existing_performer.id = "performer-123"
        existing_performer.name = "Old Name"

        # Setup mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_performer
        mock_db_session.execute.return_value = mock_result

        # Sync performer
        stats = await entity_sync_handler.sync_performers(
            [sample_performer_data], mock_db_session
        )

        # Verify stats
        assert stats["processed"] == 1
        assert stats["created"] == 0
        assert stats["updated"] == 1
        assert stats["skipped"] == 0
        assert stats["failed"] == 0

        # Verify performer was updated
        assert existing_performer.name == "Test Performer"
        assert existing_performer.aliases == ["Alias 1", "Alias 2"]

    @pytest.mark.asyncio
    async def test_sync_performers_skip_unchanged(
        self, entity_sync_handler, mock_db_session, sample_performer_data
    ):
        """Test skipping unchanged performers"""
        # Create existing performer
        existing_performer = MagicMock(spec=Performer)
        existing_performer.id = "performer-123"

        # Setup mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_performer
        mock_db_session.execute.return_value = mock_result

        # Configure strategy to skip
        entity_sync_handler.strategy.should_sync.return_value = False

        # Sync performer
        stats = await entity_sync_handler.sync_performers(
            [sample_performer_data], mock_db_session
        )

        # Verify stats
        assert stats["processed"] == 1
        assert stats["created"] == 0
        assert stats["updated"] == 0
        assert stats["skipped"] == 1
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_sync_performers_handle_errors(
        self, entity_sync_handler, mock_db_session, sample_performer_data
    ):
        """Test error handling during performer sync"""
        # Setup database to raise error
        mock_db_session.execute.side_effect = Exception("Database error")

        # Sync performer
        stats = await entity_sync_handler.sync_performers(
            [sample_performer_data], mock_db_session
        )

        # Verify stats
        assert stats["processed"] == 0
        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_sync_performers_incremental(
        self, entity_sync_handler, mock_stash_service, mock_db_session
    ):
        """Test incremental performer sync"""
        since = datetime(2023, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Mock stash service to return performers
        mock_stash_service.get_performers_since = AsyncMock(
            return_value=[{"id": "perf-1", "name": "Performer 1"}]
        )

        # Setup mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Perform incremental sync
        stats = await entity_sync_handler.sync_performers_incremental(
            since, mock_db_session
        )

        # Verify stash service was called with correct timestamp
        mock_stash_service.get_performers_since.assert_called_once_with(since)
        assert stats["processed"] == 1

    @pytest.mark.asyncio
    async def test_sync_tags_success(
        self, entity_sync_handler, mock_db_session, sample_tag_data
    ):
        """Test successful tag synchronization"""
        # Setup mock database response - no existing tag
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Sync single tag
        stats = await entity_sync_handler.sync_tags([sample_tag_data], mock_db_session)

        # Verify stats
        assert stats["processed"] == 1
        assert stats["created"] == 1
        assert stats["updated"] == 0
        assert stats["skipped"] == 0
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_sync_tags_with_parent(
        self, entity_sync_handler, mock_db_session, sample_tag_data
    ):
        """Test syncing tag with parent reference"""
        # Setup mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Sync tag
        await entity_sync_handler.sync_tags([sample_tag_data], mock_db_session)

        # Verify tag was created with parent temp ID
        created_tag = mock_db_session.add.call_args[0][0]
        assert hasattr(created_tag, "parent_temp_id")
        assert created_tag.parent_temp_id == "parent-tag-123"

    @pytest.mark.asyncio
    async def test_sync_studios_success(
        self, entity_sync_handler, mock_db_session, sample_studio_data
    ):
        """Test successful studio synchronization"""
        # Setup mock database response - no existing studio
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Sync single studio
        stats = await entity_sync_handler.sync_studios(
            [sample_studio_data], mock_db_session
        )

        # Verify stats
        assert stats["processed"] == 1
        assert stats["created"] == 1
        assert stats["updated"] == 0
        assert stats["skipped"] == 0
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_find_or_create_entity_existing(
        self, entity_sync_handler, mock_db_session
    ):
        """Test find_or_create_entity when entity exists"""
        # Create existing performer
        existing_performer = MagicMock(spec=Performer)
        existing_performer.id = "performer-123"
        existing_performer.name = "Existing Performer"

        # Setup mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_performer
        mock_db_session.execute.return_value = mock_result

        # Find entity
        result = await entity_sync_handler.find_or_create_entity(
            Performer, "performer-123", "New Name", mock_db_session
        )

        # Should return existing entity
        assert result == existing_performer
        assert not mock_db_session.add.called

    @pytest.mark.asyncio
    async def test_find_or_create_entity_create_new(
        self, entity_sync_handler, mock_db_session
    ):
        """Test find_or_create_entity when entity doesn't exist"""
        # Setup mock database response - no existing entity
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Find/create entity
        result = await entity_sync_handler.find_or_create_entity(
            Performer, "performer-123", "New Performer", mock_db_session
        )

        # Should create new entity
        assert result.id == "performer-123"
        assert result.name == "New Performer"
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_single_entity_missing_id(
        self, entity_sync_handler, mock_db_session
    ):
        """Test syncing entity without ID raises error"""
        with pytest.raises(ValueError, match="Entity ID is required"):
            await entity_sync_handler._sync_single_entity(
                Performer, {"name": "No ID"}, mock_db_session
            )

    @pytest.mark.asyncio
    async def test_sync_single_entity_force_update(
        self, entity_sync_handler, mock_db_session, sample_performer_data
    ):
        """Test force update bypasses strategy check"""
        # Create existing performer
        existing_performer = MagicMock(spec=Performer)
        existing_performer.id = "performer-123"

        # Setup mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_performer
        mock_db_session.execute.return_value = mock_result

        # Configure strategy to skip (but force should override)
        entity_sync_handler.strategy.should_sync.return_value = False

        # Sync with force=True
        result = await entity_sync_handler._sync_single_entity(
            Performer, sample_performer_data, mock_db_session, force=True
        )

        # Should update despite strategy saying no
        assert result == "updated"
        # Strategy should not be consulted when force=True
        assert not entity_sync_handler.strategy.should_sync.called

    @pytest.mark.asyncio
    async def test_resolve_tag_hierarchy(self, entity_sync_handler, mock_db_session):
        """Test resolving tag parent-child relationships"""
        # Create tags with parent references
        child_tag = MagicMock(spec=Tag)
        child_tag.id = "child-tag"
        child_tag.parent_temp_id = "parent-tag"

        parent_tag = MagicMock(spec=Tag)
        parent_tag.id = "parent-tag"

        # Setup mock database responses
        mock_results = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[child_tag]))
                )
            ),
            MagicMock(scalar_one_or_none=MagicMock(return_value=parent_tag)),
        ]
        mock_db_session.execute.side_effect = mock_results

        # Resolve hierarchy
        await entity_sync_handler.resolve_tag_hierarchy(mock_db_session)

        # Verify parent was set
        assert child_tag.parent_id == "parent-tag"

    @pytest.mark.asyncio
    async def test_resolve_tag_hierarchy_missing_parent(
        self, entity_sync_handler, mock_db_session
    ):
        """Test resolving tag hierarchy when parent doesn't exist"""
        # Create tag with missing parent reference
        child_tag = MagicMock(spec=Tag)
        child_tag.id = "child-tag"
        child_tag.parent_temp_id = "missing-parent"

        # Setup mock database responses
        mock_results = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[child_tag]))
                )
            ),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        mock_db_session.execute.side_effect = mock_results

        # Resolve hierarchy
        await entity_sync_handler.resolve_tag_hierarchy(mock_db_session)

        # Parent temp ID should be cleared
        assert child_tag.parent_temp_id is None

    @pytest.mark.asyncio
    async def test_resolve_studio_hierarchy(self, entity_sync_handler, mock_db_session):
        """Test resolving studio parent-child relationships"""
        # Create studios with parent references
        child_studio = MagicMock(spec=Studio)
        child_studio.id = "child-studio"
        child_studio.parent_temp_id = "parent-studio"

        parent_studio = MagicMock(spec=Studio)
        parent_studio.id = "parent-studio"

        # Setup mock database responses
        mock_results = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[child_studio]))
                )
            ),
            MagicMock(scalar_one_or_none=MagicMock(return_value=parent_studio)),
        ]
        mock_db_session.execute.side_effect = mock_results

        # Resolve hierarchy
        await entity_sync_handler.resolve_studio_hierarchy(mock_db_session)

        # Verify parent was set
        assert child_studio.parent_id == "parent-studio"

    def test_update_performer_all_fields(
        self, entity_sync_handler, sample_performer_data
    ):
        """Test updating all performer fields"""
        performer = MagicMock(spec=Performer)

        entity_sync_handler._update_performer(performer, sample_performer_data)

        # Verify all fields were updated
        assert performer.name == "Test Performer"
        assert performer.aliases == ["Alias 1", "Alias 2"]
        assert performer.gender == "FEMALE"
        assert performer.birthdate == "1990-01-01"
        assert performer.country == "USA"
        assert performer.ethnicity == "Caucasian"
        assert performer.hair_color == "Blonde"
        assert performer.eye_color == "Blue"
        assert performer.height_cm == 170
        assert performer.weight_kg == 60
        assert performer.measurements == "36-24-36"
        assert performer.fake_tits is False
        assert performer.career_length == "2010-2020"
        assert performer.tattoos == "Butterfly on ankle"
        assert performer.piercings == "Ears"
        assert performer.url == "http://example.com/performer"
        assert performer.twitter == "@performer"
        assert performer.instagram == "@performer"
        assert performer.details == "Test performer details"
        assert performer.rating == 5
        assert performer.favorite is True
        assert performer.ignore_auto_tag is False
        assert performer.image_url == "http://example.com/image.jpg"

    def test_update_tag_all_fields(self, entity_sync_handler, sample_tag_data):
        """Test updating all tag fields"""
        tag = MagicMock(spec=Tag)

        entity_sync_handler._update_tag(tag, sample_tag_data)

        # Verify all fields were updated
        assert tag.name == "Test Tag"
        assert tag.aliases == ["Tag Alias 1"]
        assert tag.description == "Test tag description"
        assert tag.ignore_auto_tag is False
        assert tag.parent_temp_id == "parent-tag-123"

    def test_update_studio_all_fields(self, entity_sync_handler, sample_studio_data):
        """Test updating all studio fields"""
        studio = MagicMock(spec=Studio)

        entity_sync_handler._update_studio(studio, sample_studio_data)

        # Verify all fields were updated
        assert studio.name == "Test Studio"
        assert studio.aliases == ["Studio Alias"]
        assert studio.url == "http://example.com/studio"
        assert studio.details == "Test studio details"
        assert studio.rating == 4
        assert studio.favorite is False
        assert studio.ignore_auto_tag is True
        assert studio.parent_temp_id == "parent-studio-123"
        assert studio.image_url == "http://example.com/studio.jpg"

    @pytest.mark.asyncio
    async def test_sync_with_regular_session(
        self, entity_sync_handler, sample_performer_data
    ):
        """Test sync with regular (non-async) database session"""
        # Create regular session mock
        regular_session = MagicMock()
        regular_session.execute = MagicMock()
        regular_session.add = MagicMock()
        regular_session.flush = MagicMock()

        # Setup mock response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        regular_session.execute.return_value = mock_result

        # Sync should work with regular session
        stats = await entity_sync_handler.sync_performers(
            [sample_performer_data], regular_session
        )

        assert stats["processed"] == 1
        assert stats["created"] == 1
        # Verify non-async methods were called
        regular_session.execute.assert_called()
        regular_session.flush.assert_called()
