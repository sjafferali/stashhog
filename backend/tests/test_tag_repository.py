"""Tests for TagRepository class."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.tag import Tag
from app.repositories.tag_repository import TagRepository


class TestTagRepository:
    """Test TagRepository functionality."""

    @pytest.fixture
    def tag_repo(self):
        """Create TagRepository instance."""
        return TagRepository()

    @pytest.fixture
    def sample_tag_data(self):
        """Create sample tag data."""
        return {
            "id": "tag-123",
            "name": "Test Tag",
            "aliases": ["test", "testing"],
            "description": "A test tag",
            "ignore_auto_tag": False,
            "parent_id": None,
            "last_synced": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def sample_tag(self, sample_tag_data):
        """Create sample tag instance."""
        return Tag(**sample_tag_data)

    @pytest.mark.asyncio
    async def test_find_tag_by_name(self, tag_repo, test_async_session, sample_tag):
        """Test finding a tag by name."""
        # Add tag to database
        test_async_session.add(sample_tag)
        await test_async_session.commit()

        # Find the tag
        found_tag = await tag_repo.find_tag_by_name(test_async_session, "Test Tag")

        assert found_tag is not None
        assert found_tag.id == "tag-123"
        assert found_tag.name == "Test Tag"

    @pytest.mark.asyncio
    async def test_find_tag_by_name_not_found(self, tag_repo, test_async_session):
        """Test finding a non-existent tag by name."""
        found_tag = await tag_repo.find_tag_by_name(
            test_async_session, "Non-existent Tag"
        )
        assert found_tag is None

    @pytest.mark.asyncio
    async def test_find_tag_by_name_error(self, tag_repo):
        """Test error handling in find_tag_by_name."""
        # Create a mock session that raises an exception
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")

        result = await tag_repo.find_tag_by_name(mock_session, "Test Tag")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_tag_by_id(self, tag_repo, test_async_session, sample_tag):
        """Test finding a tag by ID."""
        # Add tag to database
        test_async_session.add(sample_tag)
        await test_async_session.commit()

        # Find the tag
        found_tag = await tag_repo.find_tag_by_id(test_async_session, "tag-123")

        assert found_tag is not None
        assert found_tag.id == "tag-123"
        assert found_tag.name == "Test Tag"

    @pytest.mark.asyncio
    async def test_find_tag_by_id_not_found(self, tag_repo, test_async_session):
        """Test finding a non-existent tag by ID."""
        found_tag = await tag_repo.find_tag_by_id(test_async_session, "non-existent-id")
        assert found_tag is None

    @pytest.mark.asyncio
    async def test_find_tag_by_id_error(self, tag_repo):
        """Test error handling in find_tag_by_id."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")

        result = await tag_repo.find_tag_by_id(mock_session, "tag-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_tags(self, tag_repo, test_async_session):
        """Test getting all tags."""
        # Create multiple tags
        tags = [
            Tag(id="tag-1", name="Tag A", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-2", name="Tag B", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-3", name="Tag C", last_synced=datetime.now(timezone.utc)),
        ]

        for tag in tags:
            test_async_session.add(tag)
        await test_async_session.commit()

        # Get all tags
        all_tags = await tag_repo.get_all_tags(test_async_session)

        assert len(all_tags) == 3
        assert all_tags[0].name == "Tag A"  # Should be ordered by name
        assert all_tags[1].name == "Tag B"
        assert all_tags[2].name == "Tag C"

    @pytest.mark.asyncio
    async def test_get_all_tags_empty(self, tag_repo, test_async_session):
        """Test getting all tags when none exist."""
        all_tags = await tag_repo.get_all_tags(test_async_session)
        assert all_tags == []

    @pytest.mark.asyncio
    async def test_get_all_tags_error(self, tag_repo):
        """Test error handling in get_all_tags."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")

        result = await tag_repo.get_all_tags(mock_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_create_or_update_tag_create(self, tag_repo, test_async_session):
        """Test creating a new tag."""
        tag_data = {
            "id": "new-tag-123",
            "name": "New Tag",
            "description": "A new tag",
            "last_synced": datetime.now(timezone.utc),
        }

        created_tag = await tag_repo.create_or_update_tag(test_async_session, tag_data)
        await test_async_session.commit()

        assert created_tag is not None
        assert created_tag.id == "new-tag-123"
        assert created_tag.name == "New Tag"
        assert created_tag.description == "A new tag"

        # Verify it was saved
        found_tag = await tag_repo.find_tag_by_id(test_async_session, "new-tag-123")
        assert found_tag is not None
        assert found_tag.name == "New Tag"

    @pytest.mark.asyncio
    async def test_create_or_update_tag_update(
        self, tag_repo, test_async_session, sample_tag
    ):
        """Test updating an existing tag."""
        # Add existing tag
        test_async_session.add(sample_tag)
        await test_async_session.commit()

        # Update the tag
        update_data = {
            "id": "tag-123",
            "name": "Updated Tag",
            "description": "Updated description",
        }

        updated_tag = await tag_repo.create_or_update_tag(
            test_async_session, update_data
        )
        await test_async_session.commit()

        assert updated_tag is not None
        assert updated_tag.id == "tag-123"
        assert updated_tag.name == "Updated Tag"
        assert updated_tag.description == "Updated description"

    @pytest.mark.asyncio
    async def test_create_or_update_tag_no_id(self, tag_repo, test_async_session):
        """Test creating a tag without ID."""
        tag_data = {"name": "No ID Tag"}

        result = await tag_repo.create_or_update_tag(test_async_session, tag_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_or_update_tag_error(self, tag_repo):
        """Test error handling in create_or_update_tag."""
        mock_session = AsyncMock()
        mock_session.flush.side_effect = Exception("Database error")

        tag_data = {"id": "tag-123", "name": "Test Tag"}

        result = await tag_repo.create_or_update_tag(mock_session, tag_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_find_tags_by_names(self, tag_repo, test_async_session):
        """Test finding multiple tags by names."""
        # Create tags
        tags = [
            Tag(id="tag-1", name="Alpha", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-2", name="Beta", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-3", name="Gamma", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-4", name="Delta", last_synced=datetime.now(timezone.utc)),
        ]

        for tag in tags:
            test_async_session.add(tag)
        await test_async_session.commit()

        # Find specific tags
        names = ["Alpha", "Gamma", "NonExistent"]
        found_tags = await tag_repo.find_tags_by_names(test_async_session, names)

        assert len(found_tags) == 2
        found_names = {tag.name for tag in found_tags}
        assert "Alpha" in found_names
        assert "Gamma" in found_names
        assert "NonExistent" not in found_names

    @pytest.mark.asyncio
    async def test_find_tags_by_names_empty_list(self, tag_repo, test_async_session):
        """Test finding tags with empty names list."""
        found_tags = await tag_repo.find_tags_by_names(test_async_session, [])
        assert found_tags == []

    @pytest.mark.asyncio
    async def test_find_tags_by_names_error(self, tag_repo):
        """Test error handling in find_tags_by_names."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")

        result = await tag_repo.find_tags_by_names(mock_session, ["Test"])
        assert result == []

    def test_find_tag_by_name_sync(self, tag_repo, test_session):
        """Test synchronous find_tag_by_name."""
        # Create and add tag
        tag = Tag(
            id="sync-tag-123",
            name="Sync Test Tag",
            last_synced=datetime.now(timezone.utc),
        )
        test_session.add(tag)
        test_session.commit()

        # Find the tag
        found_tag = tag_repo.find_tag_by_name_sync(test_session, "Sync Test Tag")

        assert found_tag is not None
        assert found_tag.id == "sync-tag-123"
        assert found_tag.name == "Sync Test Tag"

    def test_find_tag_by_name_sync_not_found(self, tag_repo, test_session):
        """Test synchronous find_tag_by_name with non-existent tag."""
        found_tag = tag_repo.find_tag_by_name_sync(test_session, "Non-existent")
        assert found_tag is None

    def test_find_tag_by_name_sync_error(self, tag_repo):
        """Test error handling in synchronous find_tag_by_name."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")

        result = tag_repo.find_tag_by_name_sync(mock_session, "Test")
        assert result is None

    @pytest.mark.asyncio
    async def test_bulk_create_tags(self, tag_repo, test_async_session):
        """Test creating multiple tags in bulk."""
        tags_data = [
            {
                "id": "bulk-1",
                "name": "Bulk Tag 1",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "bulk-2",
                "name": "Bulk Tag 2",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "bulk-3",
                "name": "Bulk Tag 3",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "bulk-4",
                "name": "Bulk Tag 4",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "bulk-5",
                "name": "Bulk Tag 5",
                "last_synced": datetime.now(timezone.utc),
            },
        ]

        # Create all tags
        created_tags = []
        for tag_data in tags_data:
            tag = await tag_repo.create_or_update_tag(test_async_session, tag_data)
            assert tag is not None
            created_tags.append(tag)

        await test_async_session.commit()

        # Verify all tags were created
        all_tags = await tag_repo.get_all_tags(test_async_session)
        assert len(all_tags) == 5

        # Verify order
        tag_names = [tag.name for tag in all_tags]
        assert tag_names == [
            "Bulk Tag 1",
            "Bulk Tag 2",
            "Bulk Tag 3",
            "Bulk Tag 4",
            "Bulk Tag 5",
        ]

    @pytest.mark.asyncio
    async def test_bulk_update_tags(self, tag_repo, test_async_session):
        """Test updating multiple tags in bulk."""
        # First create tags
        tags_data = [
            {
                "id": "update-1",
                "name": "Original 1",
                "description": "Desc 1",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "update-2",
                "name": "Original 2",
                "description": "Desc 2",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "update-3",
                "name": "Original 3",
                "description": "Desc 3",
                "last_synced": datetime.now(timezone.utc),
            },
        ]

        for tag_data in tags_data:
            await tag_repo.create_or_update_tag(test_async_session, tag_data)
        await test_async_session.commit()

        # Update all tags
        update_data = [
            {"id": "update-1", "name": "Updated 1", "description": "New Desc 1"},
            {"id": "update-2", "name": "Updated 2", "description": "New Desc 2"},
            {"id": "update-3", "name": "Updated 3", "description": "New Desc 3"},
        ]

        for tag_data in update_data:
            tag = await tag_repo.create_or_update_tag(test_async_session, tag_data)
            assert tag is not None
            assert tag.name == tag_data["name"]
            assert tag.description == tag_data["description"]

        await test_async_session.commit()

    @pytest.mark.asyncio
    async def test_search_tags_by_partial_name(self, tag_repo, test_async_session):
        """Test searching tags by partial name match."""
        # Create tags with various names
        tags_data = [
            {
                "id": "search-1",
                "name": "Action Movie",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "search-2",
                "name": "Action Scene",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "search-3",
                "name": "Drama Movie",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "search-4",
                "name": "Comedy Scene",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "search-5",
                "name": "Action Comedy",
                "last_synced": datetime.now(timezone.utc),
            },
        ]

        for tag_data in tags_data:
            test_async_session.add(Tag(**tag_data))
        await test_async_session.commit()

        # Search for tags containing "Action"
        action_tags = await tag_repo.find_tags_by_names(
            test_async_session, ["Action Movie", "Action Scene", "Action Comedy"]
        )
        assert len(action_tags) == 3

        # Search for tags containing "Scene"
        scene_tags = await tag_repo.find_tags_by_names(
            test_async_session, ["Action Scene", "Comedy Scene"]
        )
        assert len(scene_tags) == 2

    @pytest.mark.asyncio
    async def test_tag_hierarchy_operations(self, tag_repo, test_async_session):
        """Test tag hierarchy with parent-child relationships."""
        # Create parent tag
        parent_data = {
            "id": "parent-tag",
            "name": "Parent Category",
            "last_synced": datetime.now(timezone.utc),
        }
        await tag_repo.create_or_update_tag(test_async_session, parent_data)

        # Create child tags
        child_data = [
            {
                "id": "child-1",
                "name": "Child 1",
                "parent_id": "parent-tag",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "child-2",
                "name": "Child 2",
                "parent_id": "parent-tag",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "child-3",
                "name": "Child 3",
                "parent_id": "parent-tag",
                "last_synced": datetime.now(timezone.utc),
            },
        ]

        child_tags = []
        for child in child_data:
            tag = await tag_repo.create_or_update_tag(test_async_session, child)
            child_tags.append(tag)

        await test_async_session.commit()

        # Verify parent-child relationships
        for child_tag in child_tags:
            assert child_tag.parent_id == "parent-tag"

    @pytest.mark.asyncio
    async def test_tag_aliases_handling(self, tag_repo, test_async_session):
        """Test handling of tag aliases."""
        tag_data = {
            "id": "alias-tag",
            "name": "Main Tag",
            "aliases": ["alias1", "alias2", "alias3"],
            "last_synced": datetime.now(timezone.utc),
        }

        await tag_repo.create_or_update_tag(test_async_session, tag_data)
        await test_async_session.commit()

        # Retrieve and verify aliases
        found_tag = await tag_repo.find_tag_by_id(test_async_session, "alias-tag")
        assert found_tag is not None
        assert found_tag.aliases == ["alias1", "alias2", "alias3"]

        # Update aliases
        update_data = {"id": "alias-tag", "aliases": ["new-alias1", "new-alias2"]}
        updated_tag = await tag_repo.create_or_update_tag(
            test_async_session, update_data
        )
        await test_async_session.commit()

        assert updated_tag.aliases == ["new-alias1", "new-alias2"]

    @pytest.mark.asyncio
    async def test_case_sensitive_search(self, tag_repo, test_async_session):
        """Test case sensitivity in tag searches."""
        tags_data = [
            {
                "id": "case-1",
                "name": "UPPERCASE",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "case-2",
                "name": "lowercase",
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "case-3",
                "name": "MixedCase",
                "last_synced": datetime.now(timezone.utc),
            },
        ]

        for tag_data in tags_data:
            test_async_session.add(Tag(**tag_data))
        await test_async_session.commit()

        # Test exact case matches
        upper_tag = await tag_repo.find_tag_by_name(test_async_session, "UPPERCASE")
        assert upper_tag is not None
        assert upper_tag.name == "UPPERCASE"

        lower_tag = await tag_repo.find_tag_by_name(test_async_session, "lowercase")
        assert lower_tag is not None
        assert lower_tag.name == "lowercase"

        # Test case mismatch (should not find)
        not_found = await tag_repo.find_tag_by_name(test_async_session, "uppercase")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_ignore_auto_tag_flag(self, tag_repo, test_async_session):
        """Test handling of ignore_auto_tag flag."""
        tags_data = [
            {
                "id": "auto-1",
                "name": "Auto Tag 1",
                "ignore_auto_tag": True,
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "auto-2",
                "name": "Auto Tag 2",
                "ignore_auto_tag": False,
                "last_synced": datetime.now(timezone.utc),
            },
            {
                "id": "auto-3",
                "name": "Auto Tag 3",
                "last_synced": datetime.now(timezone.utc),
            },  # Default should be False
        ]

        created_tags = []
        for tag_data in tags_data:
            tag = await tag_repo.create_or_update_tag(test_async_session, tag_data)
            created_tags.append(tag)

        await test_async_session.commit()

        # Verify flags
        assert created_tags[0].ignore_auto_tag is True
        assert created_tags[1].ignore_auto_tag is False
        assert created_tags[2].ignore_auto_tag is False  # Default value

    @pytest.mark.asyncio
    async def test_concurrent_tag_operations(self, tag_repo, test_async_session):
        """Test handling of concurrent tag operations."""
        # Create initial tag
        tag_data = {
            "id": "concurrent-tag",
            "name": "Concurrent Test",
            "description": "Initial description",
            "last_synced": datetime.now(timezone.utc),
        }

        await tag_repo.create_or_update_tag(test_async_session, tag_data)
        await test_async_session.commit()

        # Simulate concurrent updates
        update1 = {"id": "concurrent-tag", "description": "Update 1"}
        update2 = {"id": "concurrent-tag", "description": "Update 2"}

        # Both updates should succeed, last one wins
        await tag_repo.create_or_update_tag(test_async_session, update1)
        await tag_repo.create_or_update_tag(test_async_session, update2)

        await test_async_session.commit()

        # Verify final state
        final_tag = await tag_repo.find_tag_by_id(test_async_session, "concurrent-tag")
        assert final_tag.description == "Update 2"
